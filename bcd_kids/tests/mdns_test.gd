extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const MDNS_SCRIPT = preload("res://src/utils/MdnsDiscovery.gd")

var _test := SUPPORT.new()
var _mdns = MDNS_SCRIPT.new()


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 2)
	_test_query_encoding()
	_test_name_helpers()
	_test_dns_name_reader()
	_test_dns_message_parser()
	_test_record_validation()
	_test_peer_building()
	await _test_one_shot_discovery()
	_test.finish(self)


func _test_query_encoding() -> void:
	var query: PackedByteArray = _mdns.call(
		"_build_query", "_bcd._tcp.local.", MDNS_SCRIPT.DNS_TYPE_PTR, false
	)
	_test.expect(not query.is_empty(), "mDNS builds a PTR query")
	_test.equal(query[0], 0, "mDNS queries use a zero transaction ID")
	_test.equal(query[5], 1, "mDNS query contains one question")
	_test.equal(
		query.slice(query.size() - 4, query.size()),
		PackedByteArray([0, MDNS_SCRIPT.DNS_TYPE_PTR, 0, MDNS_SCRIPT.DNS_CLASS_IN]),
		"mDNS query encodes type and IN class"
	)

	var unicast_query: PackedByteArray = _mdns.call(
		"_build_query", "bcd._tcp.local", MDNS_SCRIPT.DNS_TYPE_A, true
	)
	_test.equal(
		unicast_query.slice(unicast_query.size() - 2, unicast_query.size()),
		PackedByteArray([0x80, 0x01]),
		"mDNS query sets the unicast-response bit when requested"
	)
	_test.equal(
		_mdns.call("_build_query", "", MDNS_SCRIPT.DNS_TYPE_PTR, false),
		PackedByteArray(),
		"mDNS rejects an empty query name"
	)
	_test.expect(
		not _mdns.call("_send_query", PacketPeerUDP.new(), "", MDNS_SCRIPT.DNS_TYPE_PTR, false),
		"mDNS does not send a query when name encoding fails"
	)

	var schedule_socket := PacketPeerUDP.new()
	var sent_queries: Dictionary = {}
	_mdns.call("_schedule_detail_queries", schedule_socket, {}, sent_queries, false)
	schedule_socket.close()
	_test.equal(sent_queries, {}, "mDNS leaves the query set unchanged for an empty service set")


func _test_name_helpers() -> void:
	_test.equal(
		_mdns.call("_canonical_name", "  BCD-HOST.LOCAL... "),
		"bcd-host.local",
		"mDNS canonicalizes names"
	)
	_test.expect(_mdns.call("_is_service_name", "Room._bcd._tcp.local"), "mDNS recognizes service instance names")
	_test.expect(not _mdns.call("_is_service_name", "evil_bcd._tcp.local"), "mDNS rejects names without a service-type separator")
	_test.expect(not _mdns.call("_is_service_name", MDNS_SCRIPT.SERVICE_TYPE), "mDNS excludes the service type itself")
	_test.equal(
		_mdns.call("_library_code_from_service_name", "Room (Annex)._bcd._tcp.local"),
		"Annex",
		"mDNS extracts a library code in parentheses"
	)
	_test.equal(
		_mdns.call("_library_code_from_service_name", "Room._bcd._tcp.local"),
		"Room",
		"mDNS falls back to the instance name for a missing library code"
	)
	_test.equal(
		_mdns.call("_library_code_from_service_name", "Room (broken._bcd._tcp.local"),
		"Room (broken",
		"mDNS keeps an instance name when parentheses are incomplete"
	)

	for address in ["192.168.1.5", "10.0.0.2"]:
		_test.expect(_mdns.call("_is_usable_ipv4", address), "mDNS accepts a usable IPv4 address: " + address)
	for address in ["127.0.0.1", "169.254.1.2", "0.0.0.0", "::1", ""]:
		_test.expect(not _mdns.call("_is_usable_ipv4", address), "mDNS rejects an unusable address: " + address)

	_test.equal(_mdns.call("_read_u16", PackedByteArray([0x12, 0x34]), 0), 0x1234, "mDNS reads a big-endian uint16")
	_test.equal(_mdns.call("_read_u16", PackedByteArray([0x12]), 0), 0, "mDNS returns zero for a truncated uint16")
	_test.equal(_mdns.call("_read_u16", PackedByteArray([0x12, 0x34]), -1), 0, "mDNS returns zero for a negative uint16 offset")


func _test_dns_name_reader() -> void:
	var plain := _dns_name("host.local")
	var plain_result: Dictionary = _mdns.call("_read_dns_name", plain, 0)
	_test.equal(plain_result.get("name", ""), "host.local", "mDNS reads an uncompressed DNS name")
	_test.equal(plain_result.get("next_offset", -1), plain.size(), "mDNS advances past an uncompressed name")

	var pointer_data := _dns_name("host.local")
	var pointer_offset := pointer_data.size()
	pointer_data.append_array(PackedByteArray([0xc0, 0x00]))
	var pointer_result: Dictionary = _mdns.call("_read_dns_name", pointer_data, pointer_offset)
	_test.equal(pointer_result.get("name", ""), "host.local", "mDNS follows a compressed name pointer")
	_test.equal(pointer_result.get("next_offset", -1), pointer_offset + 2, "mDNS keeps the offset after a pointer")

	var bad_pointer := PackedByteArray([0xc0, 0x00])
	var bad_pointer_result: Dictionary = _mdns.call("_read_dns_name", bad_pointer, 0)
	_test.expect(not bad_pointer_result.get("valid", true), "mDNS rejects a self-referencing name pointer")
	_test.expect(
		not _mdns.call("_read_dns_name", PackedByteArray([0xc0]), 0).get("valid", true),
		"mDNS rejects a truncated name pointer"
	)
	_test.expect(
		not _mdns.call("_read_dns_name", PackedByteArray([0x40]), 0).get("valid", true),
		"mDNS rejects reserved DNS label flags"
	)
	_test.expect(
		not _mdns.call("_read_dns_name", PackedByteArray([64]), 0).get("valid", true),
		"mDNS rejects a label longer than 63 bytes"
	)
	_test.expect(
		not _mdns.call("_read_dns_name", PackedByteArray([3, 1]), 0).get("valid", true),
		"mDNS rejects a truncated DNS label"
	)
	_test.expect(
		not _mdns.call("_read_dns_name", PackedByteArray([0]), 4).get("valid", true),
		"mDNS rejects an out-of-range DNS name offset"
	)

	var long_chain := PackedByteArray([0xc0, 2, 0xc0, 4, 0xc0, 6, 0xc0, 8, 0xc0, 10, 0xc0, 12, 0xc0, 14, 0xc0, 16, 0xc0, 18, 0xc0, 20, 0xc0, 22, 0xc0, 24, 0xc0, 26, 0xc0, 28, 0xc0, 30, 0xc0, 32, 0xc0, 34, 0xc0, 36, 0xc0, 38, 0xc0, 40, 0xc0, 42, 0xc0, 44, 0xc0, 46, 0xc0, 48, 0xc0, 50, 0xc0, 52, 0xc0, 54, 0xc0, 56, 0xc0, 58, 0xc0, 60, 0xc0, 62, 0xc0, 64, 0xc0, 66])
	_test.expect(
		not _mdns.call("_read_dns_name", long_chain, 0).get("valid", true),
		"mDNS rejects a name pointer chain that exceeds its safety limit"
	)


func _test_dns_message_parser() -> void:
	var packet := PackedByteArray()
	packet.resize(12)
	for index in range(packet.size()):
		packet[index] = 0
	# Three answers (PTR, SRV, TXT) and one additional A record.
	packet[7] = 3
	packet[11] = 1

	var service_name := "Reading Room (Annex)._bcd._tcp.local"
	var host_name := "bcd-host.local"
	_append_record(packet, MDNS_SCRIPT.SERVICE_TYPE, MDNS_SCRIPT.DNS_TYPE_PTR, _dns_name(service_name))

	var srv_data := PackedByteArray()
	_append_u16(srv_data, 0)
	_append_u16(srv_data, 0)
	_append_u16(srv_data, 8888)
	srv_data.append_array(_dns_name(host_name))
	_append_record(packet, service_name, MDNS_SCRIPT.DNS_TYPE_SRV, srv_data)

	var txt_data := PackedByteArray()
	_append_txt(txt_data, "library_code=Annexe")
	_append_txt(txt_data, "secure")
	_append_record(packet, service_name, MDNS_SCRIPT.DNS_TYPE_TXT, txt_data)
	_append_record(packet, host_name, MDNS_SCRIPT.DNS_TYPE_A, PackedByteArray([192, 168, 1, 20]))

	var services: Dictionary = {}
	var host_addresses: Dictionary = {}
	_mdns.call("_parse_message", packet, services, host_addresses)
	var canonical_service := "reading room (annex)._bcd._tcp.local"
	_test.expect(services.has(canonical_service), "mDNS creates a service from a PTR record")
	_test.equal(services[canonical_service].get("host", ""), host_name, "mDNS reads the SRV target")
	_test.equal(services[canonical_service].get("port", 0), 8888, "mDNS reads the SRV port")
	_test.equal(
		services[canonical_service].get("properties", {}).get("library_code", ""),
		"Annexe",
		"mDNS reads the library code from TXT properties"
	)
	_test.equal(
		services[canonical_service].get("properties", {}).get("secure", "missing"),
		"",
		"mDNS supports TXT flags without a value"
	)
	_test.equal(host_addresses.get(host_name, []), ["192.168.1.20"], "mDNS stores IPv4 A records")

	var peers: Array = _mdns.call("_build_peers", services, host_addresses)
	_test.equal(peers.size(), 1, "mDNS builds one peer from complete DNS-SD records")
	if peers.size() == 1:
		_test.equal(peers[0].get("library_code", ""), "Annexe", "mDNS exposes the TXT library code")
		_test.equal(peers[0].get("url", ""), "http://192.168.1.20:8888", "mDNS builds the peer HTTP URL")
		_test.equal(peers[0].get("name", ""), canonical_service + ".", "mDNS preserves the service name")

	var malformed_services: Dictionary = {}
	var malformed_hosts: Dictionary = {}
	_mdns.call("_parse_message", PackedByteArray([0, 0, 0, 0]), malformed_services, malformed_hosts)
	_test.expect(malformed_services.is_empty(), "mDNS ignores packets shorter than a DNS header")

	var bad_question := PackedByteArray()
	bad_question.resize(12)
	for index in range(bad_question.size()):
		bad_question[index] = 0
	bad_question[5] = 1
	bad_question.append(0xc0)
	_mdns.call("_parse_message", bad_question, malformed_services, malformed_hosts)
	_test.expect(
		malformed_services.is_empty() and malformed_hosts.is_empty(),
		"mDNS ignores malformed question sections without raising"
	)


func _test_record_validation() -> void:
	var services: Dictionary = {}
	var hosts: Dictionary = {}
	var empty_data := PackedByteArray()

	_mdns.call("_apply_record", empty_data, MDNS_SCRIPT.SERVICE_TYPE, MDNS_SCRIPT.DNS_TYPE_PTR, 1, 0, 0, services, hosts)
	_mdns.call("_apply_record", empty_data, "wrong._bcd._tcp.local", MDNS_SCRIPT.DNS_TYPE_SRV, 1, 0, 0, services, hosts)
	var wrong_ptr_target := _dns_name("unrelated.local")
	_mdns.call("_apply_record", wrong_ptr_target, MDNS_SCRIPT.SERVICE_TYPE, MDNS_SCRIPT.DNS_TYPE_PTR, 1, 0, 0, services, hosts)
	_mdns.call("_apply_record", wrong_ptr_target, MDNS_SCRIPT.SERVICE_TYPE, MDNS_SCRIPT.DNS_TYPE_PTR, 2, 0, 0, services, hosts)
	_mdns.call("_apply_record", empty_data, "not-service.local", MDNS_SCRIPT.DNS_TYPE_TXT, 1, 0, 0, services, hosts)
	_mdns.call("_apply_record", empty_data, "bcd-host.local", MDNS_SCRIPT.DNS_TYPE_A, 1, 0, 3, services, hosts)
	_test.expect(services.is_empty(), "mDNS rejects malformed PTR, wrong-class, SRV, TXT, and A records")

	var txt_data := PackedByteArray([5, 65, 66])
	_test.equal(
		_mdns.call("_parse_txt_properties", txt_data, 0, txt_data.size()),
		{},
		"mDNS stops parsing a truncated TXT value"
	)

	var no_library_services := {
		"Book._bcd._tcp.local": {"host": "book.local", "port": 9000, "properties": {}}
	}
	var no_library_hosts := {"book.local": ["10.0.0.7"]}
	var peers: Array = _mdns.call("_build_peers", no_library_services, no_library_hosts)
	_test.equal(peers[0].get("library_code", ""), "Book", "mDNS derives a library code when TXT is absent")


func _test_peer_building() -> void:
	var services := {
		"missing-host._bcd._tcp.local": {"host": "", "port": 8888, "properties": {}},
		"missing-port._bcd._tcp.local": {"host": "host.local", "port": 0, "properties": {}},
		"missing-address._bcd._tcp.local": {"host": "unknown.local", "port": 8888, "properties": {}},
	}
	_test.equal(_mdns.call("_build_peers", services, {}), [], "mDNS skips incomplete services")

	var ensured: Dictionary = _mdns.call("_ensure_service", services, "New Room._bcd._tcp.local.")
	_test.equal(ensured.get("name", ""), "new room._bcd._tcp.local", "mDNS normalizes newly created services")
	_test.equal(
		_mdns.call("_ensure_service", services, "New Room._bcd._tcp.local"),
		ensured,
		"mDNS reuses an existing normalized service"
	)
	_test.equal(_mdns.call("_parse_txt_properties", PackedByteArray(), 0, 0), {}, "mDNS accepts an empty TXT record")
	_test.equal(
		_mdns.call("_parse_txt_properties", PackedByteArray([3, 97, 98, 99]), 0, 4),
		{"abc": ""},
		"mDNS parses a TXT flag"
	)


func _test_one_shot_discovery() -> void:
	var peers = await _mdns.discover(0.0)
	_test.expect(peers is Array, "mDNS one-shot discovery returns an Array without a server")


func _dns_name(name: String) -> PackedByteArray:
	var result := PackedByteArray()
	var normalized := str(_mdns.call("_canonical_name", name))
	if normalized.is_empty():
		result.append(0)
		return result
	for label in normalized.split("."):
		var bytes := label.to_utf8_buffer()
		result.append(bytes.size())
		result.append_array(bytes)
	result.append(0)
	return result


func _append_u16(packet: PackedByteArray, value: int) -> void:
	packet.append((value >> 8) & 0xff)
	packet.append(value & 0xff)


func _append_u32(packet: PackedByteArray, value: int) -> void:
	packet.append((value >> 24) & 0xff)
	packet.append((value >> 16) & 0xff)
	packet.append((value >> 8) & 0xff)
	packet.append(value & 0xff)


func _append_record(packet: PackedByteArray, name: String, record_type: int, data: PackedByteArray) -> void:
	packet.append_array(_dns_name(name))
	_append_u16(packet, record_type)
	_append_u16(packet, MDNS_SCRIPT.DNS_CLASS_IN)
	_append_u32(packet, 120)
	_append_u16(packet, data.size())
	packet.append_array(data)


func _append_txt(packet: PackedByteArray, value: String) -> void:
	var bytes := value.to_utf8_buffer()
	packet.append(bytes.size())
	packet.append_array(bytes)
