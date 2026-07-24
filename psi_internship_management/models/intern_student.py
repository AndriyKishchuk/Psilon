import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternStudent(models.Model):
    _name = "psi.intern.student"
    _description = "Intern Student"
    _order = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Imie i nazwisko", required=True, tracking=True)
    phone = fields.Char(string="Telefon")
    email = fields.Char(string="Email", tracking=True)
    image_1920 = fields.Image(string="Zdjecie")
    user_id = fields.Many2one("res.users", string="Uzytkownik systemu")

    start_date = fields.Date(string="Data rozpoczecia", tracking=True)
    end_date = fields.Date(string="Data zakonczenia", tracking=True)
    supervisor_id = fields.Many2one("res.users", string="Opiekun", required=True, tracking=True)
    school = fields.Char(string="Szkola/Uczelnia", required=True, tracking=True)
    field_of_study = fields.Char(string="Kierunek/Profil", required=True, tracking=True)
    required_hours = fields.Integer(
        string="Wymagana liczba godzin",
        required=True,
        tracking=True,
    )
    total_attendance_hours = fields.Float(
        string="Suma godzin",
        compute="_compute_total_attendance_hours",
        store=True,
    )
    is_cancelled = fields.Boolean(string="Praktyka anulowana", default=False, tracking=True)
    status = fields.Selection(
        [
            ("new", "Nowy"),
            ("active", "Aktywny"),
            ("finished", "Zakonczony"),
            ("cancelled", "Anulowany"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,
        readonly=True,
        tracking=True,
    )
    attendance_ids = fields.One2many(
        "psi.intern.attendance",
        "intern_id",
        string="Plan obecnosci",
    )

    birthdate = fields.Date(string="Data urodzenia")
    street = fields.Char(string="Ulica")
    city = fields.Char(string="Miasto")
    zip_code = fields.Char(string="Kod pocztowy")
    country = fields.Char(string="Kraj")

    education_notes = fields.Text(string="Wyksztalcenie")
    experience_notes = fields.Text(string="Doswiadczenie")
    skills_notes = fields.Text(string="Umiejetnosci")
    language_ids = fields.One2many(
        "psi.intern.language",
        "intern_id",
        string="Jezyki",
    )
    resume_file = fields.Binary(string="Plik CV")
    resume_filename = fields.Char(string="Nazwa pliku CV")

    document_ids = fields.Many2many(
        "ir.attachment",
        "psi_intern_student_ir_attachments_rel",
        "intern_id",
        "attachment_id",
        string="Dokumenty",
    )

    active = fields.Boolean(string="Aktywny", default=True)
    notes = fields.Text(string="Notatki", tracking=True)

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError(
                    "Data zakonczenia nie moze byc wczesniejsza niz data rozpoczecia."
                )

    @api.constrains("email")
    def _check_email(self):
        for record in self:
            if record.email and "@" not in record.email:
                raise ValidationError("Adres email musi zawierac znak @.")

    @api.constrains("phone")
    def _check_phone(self):
        for record in self:
            if record.phone:
                cleaned_phone = record.phone.replace(" ", "")
                if not cleaned_phone.isdigit():
                    raise ValidationError("Numer telefonu moze zawierac tylko cyfry.")
                if len(cleaned_phone) != 9:
                    raise ValidationError("Numer telefonu musi miec dokladnie 9 cyfr.")

    @api.constrains("status", "end_date")
    def _check_finished_requires_end_date(self):
        for record in self:
            if record.status == "finished" and not record.end_date:
                raise ValidationError(
                    "Dla zakonczonej praktyki data zakonczenia jest wymagana."
                )

    @api.constrains("status", "start_date")
    def _check_active_requires_start_date(self):
        for record in self:
            if record.status in ("active", "finished") and not record.start_date:
                raise ValidationError(
                    "Dla aktywnej praktyki data rozpoczecia jest wymagana."
                )

    @api.constrains("birthdate")
    def _check_birthdate(self):
        for record in self:
            if record.birthdate and record.birthdate > fields.Date.today():
                raise ValidationError("Data urodzenia nie moze byc z przyszlosci.")

    @api.constrains("city")
    def _check_city(self):
        for record in self:
            if record.city and any(char.isdigit() for char in record.city):
                raise ValidationError("Miasto nie moze zawierac cyfr.")

    @api.constrains("country")
    def _check_country(self):
        for record in self:
            if record.country and any(char.isdigit() for char in record.country):
                raise ValidationError("Kraj nie moze zawierac cyfr.")

    @api.constrains("zip_code")
    def _check_zip_code(self):
        pattern = r"^\d{2}-\d{3}$"
        for record in self:
            if record.zip_code and not re.match(pattern, record.zip_code):
                raise ValidationError("Kod pocztowy musi miec format, np. 35-505.")

    @api.constrains("required_hours")
    def _check_required_hours(self):
        for record in self:
            if record.required_hours <= 0:
                raise ValidationError("Wymagana liczba godzin musi byc wieksza od 0.")

    @api.depends("attendance_ids.duration_hours")
    def _compute_total_attendance_hours(self):
        for record in self:
            record.total_attendance_hours = sum(record.attendance_ids.mapped("duration_hours"))

    def _get_status_from_progress(self):
        self.ensure_one()
        today = fields.Date.today()

        if self.is_cancelled:
            return "cancelled"
        if not self.start_date:
            return "new"
        if self.required_hours and self.total_attendance_hours >= self.required_hours:
            return "finished"
        if self.end_date and today > self.end_date:
            return "finished"
        if today < self.start_date:
            return "new"
        return "active"

    @api.depends("start_date", "end_date", "required_hours", "total_attendance_hours", "is_cancelled")
    def _compute_status(self):
        for record in self:
            record.status = record._get_status_from_progress()

    def action_cancel_practice(self):
        for record in self:
            if record.is_cancelled:
                continue

            if record.user_id and record.user_id.share:
                portal_user = record.user_id.sudo()
                other_students = self.env["psi.intern.student"].sudo().search_count(
                    [("user_id", "=", portal_user.id), ("id", "!=", record.id)]
                )
                record.user_id = False
                if not other_students:
                    portal_user.unlink()

            record.is_cancelled = True

    def action_restore_practice(self):
        for record in self:
            if not record.is_cancelled:
                continue
            record.is_cancelled = False

    def unlink(self):
        applications = self.env["psi.intern.application"].sudo().search(
            [("student_id", "in", self.ids)]
        )
        if applications:
            applications.unlink()

        for record in self:
            if record.document_ids:
                record.document_ids = [(5, 0, 0)]
            if record.user_id and record.user_id.share:
                portal_user = record.user_id.sudo()
                other_students = self.env["psi.intern.student"].sudo().search_count(
                    [("user_id", "=", portal_user.id), ("id", "!=", record.id)]
                )
                record.user_id = False
                if not other_students:
                    portal_user.unlink()

        return super().unlink()
