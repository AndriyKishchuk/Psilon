import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternStudent(models.Model):
    _name = "psi.intern.student"
    _description = "Intern Student"
    _order = "name"

    name = fields.Char(string="Imie i nazwisko", required=True)
    phone = fields.Char(string="Telefon")
    email = fields.Char(string="Email")
    image_1920 = fields.Image(string="Zdjecie")
    user_id = fields.Many2one("res.users", string="Uzytkownik systemu")

    start_date = fields.Date(string="Data rozpoczecia")
    end_date = fields.Date(string="Data zakonczenia")
    supervisor_id = fields.Many2one("res.users", string="Opiekun", required=True)
    school = fields.Char(string="Szkola/Uczelnia", required=True)
    field_of_study = fields.Char(string="Kierunek/Profil", required=True)
    required_hours = fields.Integer(string="Wymagana liczba godzin")
    total_attendance_hours = fields.Float(
        string="Suma godzin",
        compute="_compute_total_attendance_hours",
        store=True,
    )
    status = fields.Selection(
        [
            ("new", "Nowy"),
            ("active", "Aktywny"),
            ("finished", "Zakonczony"),
            ("cancelled", "Anulowany"),
        ],
        string="Status",
        default="new",
        required=True,
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
    notes = fields.Text(string="Notatki")

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

    @api.depends("attendance_ids.duration_hours")
    def _compute_total_attendance_hours(self):
        for record in self:
            record.total_attendance_hours = sum(record.attendance_ids.mapped("duration_hours"))

    @api.onchange("start_date", "end_date")
    def _onchange_status_from_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.status == "cancelled":
                continue
            if not record.start_date:
                record.status = "new"
            elif record.start_date and record.end_date:
                if today < record.start_date:
                    record.status = "new"
                elif record.start_date <= today <= record.end_date:
                    record.status = "active"
                elif today > record.end_date:
                    record.status = "finished"
            elif record.start_date and not record.end_date:
                if today < record.start_date:
                    record.status = "new"
                else:
                    record.status = "active"

    def _set_status_from_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.status == "cancelled":
                continue
            if not record.start_date:
                record.status = "new"
            elif record.start_date and record.end_date:
                if today < record.start_date:
                    record.status = "new"
                elif record.start_date <= today <= record.end_date:
                    record.status = "active"
                elif today > record.end_date:
                    record.status = "finished"
            elif record.start_date and not record.end_date:
                if today < record.start_date:
                    record.status = "new"
                else:
                    record.status = "active"

    def action_cancel_practice(self):
        for record in self:
            if record.status == "cancelled":
                continue
            record.status = "cancelled"

    def action_restore_practice(self):
        for record in self:
            if record.status != "cancelled":
                continue
            record._set_status_from_dates()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._set_status_from_dates()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "start_date" in vals or "end_date" in vals:
            self._set_status_from_dates()
        return res

    def unlink(self):
        applications = self.env["psi.intern.application"].sudo().search(
            [("student_id", "in", self.ids)]
        )
        if applications:
            applications.unlink()

        for record in self:
            if record.document_ids:
                record.document_ids = [(5, 0, 0)]
            if record.user_id:
                other_students = self.env["psi.intern.student"].sudo().search_count(
                    [("user_id", "=", record.user_id.id), ("id", "!=", record.id)]
                )
                if not other_students:
                    record.user_id.sudo().write({"active": False})

        return super().unlink()
