# Confirmation shown when a selected student has been inactive.
extends Control

signal continue_session
signal change_student

@onready var _title: Label = %Title
@onready var _message: Label = %Message
@onready var _countdown: Label = %Countdown
@onready var _yes_button: Button = %YesButton
@onready var _change_student_button: Button = %ChangeStudentButton
@onready var _grace_timer: Timer = $GraceTimer

var _borrower_name := ""

func _ready() -> void:
	_yes_button.pressed.connect(func(): continue_session.emit())
	_change_student_button.pressed.connect(func(): change_student.emit())
	_grace_timer.timeout.connect(func(): change_student.emit())
	_refresh_content()
	_grace_timer.start(Settings.STUDENT_PRESENCE_GRACE_SECONDS)
	_refresh_countdown()
	_yes_button.call_deferred("grab_focus")

func setup(borrower_name: String) -> void:
	_borrower_name = borrower_name
	if is_node_ready():
		_refresh_content()

func _refresh_content() -> void:
	_title.text = I18n.t("presence.title", {"name": _borrower_name})
	_message.text = I18n.t("presence.message", {"seconds": Settings.STUDENT_PRESENCE_GRACE_SECONDS})
	_yes_button.text = I18n.t("presence.yes")
	_change_student_button.text = I18n.t("presence.change_student")

func _process(_delta: float) -> void:
	_refresh_countdown()

func _refresh_countdown() -> void:
	if not is_node_ready():
		return
	var seconds_left := int(ceil(_grace_timer.time_left))
	_countdown.text = I18n.t("presence.countdown", {"seconds": seconds_left})
