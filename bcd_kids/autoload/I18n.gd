# Autoload "I18n" - Internationalization System
extends Node

var current_locale := "fr"  # Default to French
var translations := {}

signal locale_changed(locale: String)

func _ready():
	load_translations()

func load_translations():
	for locale in ["fr", "en"]:
		var file_path = "res://locales/%s.json" % locale
		var file = FileAccess.open(file_path, FileAccess.READ)
		if file:
			var json_string = file.get_as_text()
			var json = JSON.new()
			var error = json.parse(json_string)
			if error == OK:
				translations[locale] = json.data
			file.close()

func t(key: String, params: Dictionary = {}) -> String:
	var keys = key.split(".")
	var data = translations.get(current_locale, {})

	for k in keys:
		if data is Dictionary and data.has(k):
			data = data[k]
		else:
			return key

	var text = str(data)

	for param_key in params:
		text = text.replace("{%s}" % param_key, str(params[param_key]))

	return text

func set_locale(locale: String):
	if locale in ["fr", "en"]:
		current_locale = locale
		locale_changed.emit(locale)
