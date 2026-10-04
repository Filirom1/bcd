# Lightweight DNS-SD/mDNS client for discovering BCD servers.
#
# This intentionally uses IPv4 addresses returned in A records instead of
# resolving the advertised .local hostname through the operating system.
# That keeps discovery independent from Avahi/NSS configuration on the client.
class_name MdnsDiscovery
extends RefCounted

const SERVICE_TYPE := "_bcd._tcp.local"
const MDNS_ADDRESS := "224.0.0.251"
const MDNS_PORT := 5353
const DNS_CLASS_IN := 1
const DNS_TYPE_A := 1
const DNS_TYPE_PTR := 12
const DNS_TYPE_TXT := 16
const DNS_TYPE_SRV := 33
const MAX_NAME_POINTERS := 32


## Discover BCD DNS-SD services visible on the local IPv4 network.
##
## The returned dictionaries deliberately match the shape of the API
## /collections/peers response so the screen can display either source.
func discover(timeout_seconds: float = 2.0) -> Array:
	var socket := PacketPeerUDP.new()
	var request_unicast_response := false
	var bind_error := socket.bind(MDNS_PORT, "*")
	if bind_error != OK:
		# Avahi or another mDNS daemon may already own UDP/5353. A legacy
		# one-shot mDNS query from an ephemeral port asks responders to send
		# the answer back to that port, so discovery can coexist with Avahi.
		print("[mDNS] UDP/%d is busy (%s); using an ephemeral query socket" % [MDNS_PORT, error_string(bind_error)])
		socket.close()
		socket = PacketPeerUDP.new()
		var fallback_bind_error := socket.bind(0, "*")
		if fallback_bind_error != OK:
			print("[mDNS] Cannot bind fallback UDP socket: %s" % error_string(fallback_bind_error))
			return []
		request_unicast_response = true

	var joined_interfaces: Array = []
	if not request_unicast_response:
		joined_interfaces = _join_ipv4_interfaces(socket)
		if joined_interfaces.is_empty():
			print("[mDNS] No usable IPv4 multicast interface found")
			socket.close()
			return []

	var services: Dictionary = {}
	var host_addresses: Dictionary = {}
	var sent_queries: Dictionary = {}

	_send_query(socket, SERVICE_TYPE, DNS_TYPE_PTR, request_unicast_response)
	sent_queries["%s|%d" % [SERVICE_TYPE, DNS_TYPE_PTR]] = true

	var deadline := Time.get_ticks_msec() + maxi(1, int(timeout_seconds * 1000.0))
	while Time.get_ticks_msec() < deadline:
		while socket.get_available_packet_count() > 0:
			var packet := socket.get_packet()
			_parse_message(packet, services, host_addresses)

		_schedule_detail_queries(socket, services, sent_queries, request_unicast_response)
		await _wait_one_frame()

	var peers := _build_peers(services, host_addresses)
	for interface_name in joined_interfaces:
		socket.leave_multicast_group(MDNS_ADDRESS, interface_name)
	socket.close()

	print("[mDNS] Discovered %d BCD server(s)" % peers.size())
	return peers


func _join_ipv4_interfaces(socket: PacketPeerUDP) -> Array:
	var joined_interfaces: Array = []
	for interface_data_variant in IP.get_local_interfaces():
		if not (interface_data_variant is Dictionary):
			continue
		var interface_data: Dictionary = interface_data_variant
		var interface_name := str(interface_data.get("name", ""))
		if interface_name.is_empty():
			continue

		var has_ipv4 := false
		for address_variant in interface_data.get("addresses", []):
			if _is_usable_ipv4(str(address_variant)):
				has_ipv4 = true
				break
		if not has_ipv4:
			continue

		var join_error := socket.join_multicast_group(MDNS_ADDRESS, interface_name)
		if join_error == OK:
			joined_interfaces.append(interface_name)
		else:
			print("[mDNS] Cannot join %s on %s: %s" % [MDNS_ADDRESS, interface_name, error_string(join_error)])

	return joined_interfaces


func _is_usable_ipv4(address: String) -> bool:
	return address.contains(".") \
		and not address.begins_with("127.") \
		and not address.begins_with("169.254.") \
		and address != "0.0.0.0"


func _send_query(
		socket: PacketPeerUDP,
		name: String,
		query_type: int,
		request_unicast_response: bool = false
) -> bool:
	var packet := _build_query(name, query_type, request_unicast_response)
	if packet.is_empty():
		return false
	var destination_error := socket.set_dest_address(MDNS_ADDRESS, MDNS_PORT)
	if destination_error != OK:
		print("[mDNS] Cannot set multicast destination: %s" % error_string(destination_error))
		return false
	return socket.put_packet(packet) == OK


func _schedule_detail_queries(
		socket: PacketPeerUDP,
		services: Dictionary,
		sent_queries: Dictionary,
		request_unicast_response: bool
) -> void:
	for service_name_variant in services.keys():
		var service_name := str(service_name_variant)
		for query_type in [DNS_TYPE_SRV, DNS_TYPE_TXT]:
			var query_key := "%s|%d" % [service_name, query_type]
			if sent_queries.has(query_key):
				continue
			_send_query(socket, service_name, query_type, request_unicast_response)
			sent_queries[query_key] = true

		var service: Dictionary = services[service_name]
		var host := str(service.get("host", ""))
		if host.is_empty():
			continue
		var address_query_key := "%s|%d" % [host, DNS_TYPE_A]
		if sent_queries.has(address_query_key):
			continue
		_send_query(socket, host, DNS_TYPE_A, request_unicast_response)
		sent_queries[address_query_key] = true


func _build_query(
		name: String,
		query_type: int,
		request_unicast_response: bool = false
) -> PackedByteArray:
	var packet := PackedByteArray()
	packet.resize(12)
	for index in range(packet.size()):
		packet[index] = 0
	# QDCOUNT = 1. mDNS queries use transaction ID 0 and flags 0.
	packet[5] = 1
	if not _append_dns_name(packet, name):
		return PackedByteArray()
	_append_u16(packet, query_type)
	var query_class := DNS_CLASS_IN | (0x8000 if request_unicast_response else 0)
	_append_u16(packet, query_class)
	return packet


func _append_dns_name(packet: PackedByteArray, name: String) -> bool:
	var normalized_name := _canonical_name(name)
	if normalized_name.is_empty():
		return false
	for label in normalized_name.split("."):
		var label_bytes := label.to_utf8_buffer()
		if label_bytes.is_empty() or label_bytes.size() > 63:
			return false
		packet.append(label_bytes.size())
		packet.append_array(label_bytes)
	packet.append(0)
	return true


func _append_u16(packet: PackedByteArray, value: int) -> void:
	packet.append((value >> 8) & 0xff)
	packet.append(value & 0xff)


func _parse_message(data: PackedByteArray, services: Dictionary, host_addresses: Dictionary) -> void:
	if data.size() < 12:
		return

	var question_count := _read_u16(data, 4)
	var answer_count := _read_u16(data, 6)
	var authority_count := _read_u16(data, 8)
	var additional_count := _read_u16(data, 10)
	var offset := 12

	for _index in range(question_count):
		var question_name := _read_dns_name(data, offset)
		if not question_name.get("valid", false):
			return
		offset = int(question_name.get("next_offset", -1))
		if offset < 0 or offset + 4 > data.size():
			return
		offset += 4

	for record_count in [answer_count, authority_count, additional_count]:
		offset = _parse_records(data, offset, record_count, services, host_addresses)
		if offset < 0:
			return


func _parse_records(
		data: PackedByteArray,
		offset: int,
		record_count: int,
		services: Dictionary,
		host_addresses: Dictionary
) -> int:
	var cursor := offset
	for _index in range(record_count):
		var record_name := _read_dns_name(data, cursor)
		if not record_name.get("valid", false):
			return -1
		cursor = int(record_name.get("next_offset", -1))
		if cursor < 0 or cursor + 10 > data.size():
			return -1

		var record_type := _read_u16(data, cursor)
		var record_class := _read_u16(data, cursor + 2)
		var record_length := _read_u16(data, cursor + 8)
		var record_start := cursor + 10
		var record_end := record_start + record_length
		if record_end > data.size():
			return -1

		_apply_record(
			data,
			_canonical_name(str(record_name.get("name", ""))),
			record_type,
			record_class,
			record_start,
			record_length,
			services,
			host_addresses
		)
		cursor = record_end

	return cursor


func _apply_record(
		data: PackedByteArray,
		record_name: String,
		record_type: int,
		record_class: int,
		record_start: int,
		record_length: int,
		services: Dictionary,
		host_addresses: Dictionary
) -> void:
	# The cache-flush bit is part of the class field, but the base class must
	# still identify an Internet record.
	if (record_class & 0x7fff) != DNS_CLASS_IN:
		return
	if record_start < 0 or record_length < 0 or record_start + record_length > data.size():
		return

	match record_type:
		DNS_TYPE_PTR:
			if record_name != SERVICE_TYPE:
				return
			var ptr_target := _read_dns_name(data, record_start)
			if not ptr_target.get("valid", false) \
				or int(ptr_target.get("next_offset", -1)) > record_start + record_length:
				return
			var target_name := _canonical_name(str(ptr_target.get("name", "")))
			# PTR records for the queried service type point to concrete instance
			# names, never to a different service type or an arbitrary hostname.
			if not _is_service_name(target_name):
				return
			_ensure_service(services, target_name)

		DNS_TYPE_SRV:
			if record_length < 7 or not _is_service_name(record_name):
				return
			var srv_target := _read_dns_name(data, record_start + 6)
			if not srv_target.get("valid", false) \
				or int(srv_target.get("next_offset", -1)) > record_start + record_length:
				return
			var srv_service := _ensure_service(services, record_name)
			srv_service["host"] = _canonical_name(str(srv_target.get("name", "")))
			srv_service["port"] = _read_u16(data, record_start + 4)

		DNS_TYPE_TXT:
			if not _is_service_name(record_name):
				return
			var txt_service := _ensure_service(services, record_name)
			txt_service["properties"] = _parse_txt_properties(data, record_start, record_length)

		DNS_TYPE_A:
			if record_length != 4:
				return
			var address := "%d.%d.%d.%d" % [
				data[record_start],
				data[record_start + 1],
				data[record_start + 2],
				data[record_start + 3]
			]
			var addresses: Array = host_addresses.get(record_name, [])
			if not addresses.has(address):
				addresses.append(address)
			host_addresses[record_name] = addresses


func _ensure_service(services: Dictionary, service_name: String) -> Dictionary:
	var canonical_name := _canonical_name(service_name)
	if not services.has(canonical_name):
		services[canonical_name] = {
			"name": canonical_name,
			"host": "",
			"port": 0,
			"properties": {},
		}
	return services[canonical_name]


func _parse_txt_properties(data: PackedByteArray, start: int, length: int) -> Dictionary:
	var properties: Dictionary = {}
	var cursor := start
	var end := start + length
	while cursor < end:
		var value_length := int(data[cursor])
		cursor += 1
		if cursor + value_length > end:
			break
		var value := data.slice(cursor, cursor + value_length).get_string_from_utf8()
		cursor += value_length
		var separator := value.find("=")
		if separator == -1:
			properties[value] = ""
		else:
			properties[value.substr(0, separator)] = value.substr(separator + 1)
	return properties


func _build_peers(services: Dictionary, host_addresses: Dictionary) -> Array:
	var peers: Array = []
	for service_name_variant in services.keys():
		var service_name := str(service_name_variant)
		var canonical_service_name := _canonical_name(service_name)
		if not _is_service_name(canonical_service_name):
			continue
		var service: Dictionary = services[service_name_variant]
		var host := str(service.get("host", ""))
		var port := int(service.get("port", 0))
		var addresses: Array = host_addresses.get(host, [])
		if host.is_empty() or port <= 0 or port > 65535 or addresses.is_empty():
			continue

		var properties: Dictionary = service.get("properties", {})
		var library_code := str(properties.get("library_code", ""))
		if library_code.is_empty():
			library_code = _library_code_from_service_name(service_name)

		var peer := {
			"name": service_name.rstrip(".") + ".",
			"library_code": library_code,
			"host": host + ".",
			"addresses": addresses.duplicate(),
			"port": port,
			"url": "http://%s:%d" % [addresses[0], port],
		}
		peers.append(peer)

	return peers


func _library_code_from_service_name(service_name: String) -> String:
	var suffix := "." + SERVICE_TYPE
	var instance_name := service_name
	if instance_name.ends_with(suffix):
		instance_name = instance_name.substr(0, instance_name.length() - suffix.length())
	var opening := instance_name.rfind("(")
	var closing := instance_name.rfind(")")
	if opening >= 0 and closing > opening:
		return instance_name.substr(opening + 1, closing - opening - 1)
	return instance_name


func _is_service_name(name: String) -> bool:
	var canonical := _canonical_name(name)
	return not canonical.is_empty() \
		and canonical != SERVICE_TYPE \
		and canonical.ends_with("." + SERVICE_TYPE)


func _read_dns_name(data: PackedByteArray, offset: int) -> Dictionary:
	if offset < 0 or offset >= data.size():
		return {"valid": false, "next_offset": -1, "name": ""}

	var labels: Array[String] = []
	var cursor := offset
	var next_offset := -1
	var jumped := false
	var visited: Dictionary = {}

	for _index in range(MAX_NAME_POINTERS):
		if cursor >= data.size():
			return {"valid": false, "next_offset": -1, "name": ""}
		var label_length := int(data[cursor])

		if label_length == 0:
			if not jumped:
				next_offset = cursor + 1
			return {
				"valid": true,
				"next_offset": next_offset,
				"name": ".".join(labels),
			}

		if (label_length & 0xc0) == 0xc0:
			if cursor + 1 >= data.size():
				return {"valid": false, "next_offset": -1, "name": ""}
			var pointer := ((label_length & 0x3f) << 8) | int(data[cursor + 1])
			# DNS compression pointers refer to an earlier name. Rejecting forward
			# pointers also prevents a crafted packet from escaping its RDATA path.
			if pointer >= cursor or pointer >= data.size() or visited.has(pointer):
				return {"valid": false, "next_offset": -1, "name": ""}
			visited[pointer] = true
			if not jumped:
				next_offset = cursor + 2
			cursor = pointer
			jumped = true
			continue

		if (label_length & 0xc0) != 0 or label_length > 63:
			return {"valid": false, "next_offset": -1, "name": ""}
		var label_start := cursor + 1
		var label_end := label_start + label_length
		if label_end > data.size():
			return {"valid": false, "next_offset": -1, "name": ""}
		labels.append(data.slice(label_start, label_end).get_string_from_utf8())
		cursor = label_end

	return {"valid": false, "next_offset": -1, "name": ""}


func _read_u16(data: PackedByteArray, offset: int) -> int:
	if offset < 0 or offset + 1 >= data.size():
		return 0
	return (int(data[offset]) << 8) | int(data[offset + 1])


func _canonical_name(name: String) -> String:
	var canonical := name.strip_edges().to_lower()
	while canonical.ends_with("."):
		canonical = canonical.substr(0, canonical.length() - 1)
	return canonical


func _wait_one_frame() -> void:
	var main_loop := Engine.get_main_loop()
	if main_loop is SceneTree:
		var tree: SceneTree = main_loop
		await tree.process_frame
