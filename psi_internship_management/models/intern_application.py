from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternApplication(models.Model):
    _name = "psi.intern.application"
    _description = "Internship Application"
    _order = "create_date desc"

    name = fields.Char(string="Imie i nazwisko", required=True)
    email = fields.Char(string="Email", required=True)
    phone = fields.Char(string="Telefon", required=True)
    school = fields.Char(string="Szkola / Uczelnia", required=True)
    field_of_study = fields.Char(string="Kierunek/Profil", required=True)
    required_hours = fields.Integer(string="Wymagana liczba godzin", required=True)
    start_date = fields.Date(string="Data rozpoczecia")
    end_date = fields.Date(string="Data zakonczenia")
    notes = fields.Text(string="Notatka")
    supervisor_id = fields.Many2one("res.users", string="Opiekun")
    registration_token = fields.Char(string="Token rejestracji", copy=False)
    user_id = fields.Many2one("res.users", string="Uzytkownik", ondelete="set null")
    student_id = fields.Many2one("psi.intern.student", string="Praktykant", ondelete="cascade")
    status = fields.Selection(
        [
            ("new", "Nowe"),
            ("approved", "Zaakceptowane"),
            ("rejected", "Odrzucone"),
        ],
        string="Status",
        default="new",
        required=True,
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

    @api.constrains("required_hours")
    def _check_required_hours(self):
        for record in self:
            if record.required_hours <= 0:
                raise ValidationError("Wymagana liczba godzin musi byc wieksza od zera.")

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError(
                    "Data zakonczenia nie moze byc wczesniejsza niz data rozpoczecia."
                )

    def action_approve(self):
        for record in self:
            if record.status != "new":
                continue

            if record.student_id:
                student = record.student_id.sudo()
                student.write(
                    {
                        "name": record.name,
                        "email": record.email,
                        "phone": record.phone,
                        "school": record.school,
                        "field_of_study": record.field_of_study,
                        "required_hours": record.required_hours,
                        "start_date": record.start_date,
                        "end_date": record.end_date,
                        "notes": record.notes,
                        "supervisor_id": record.supervisor_id.id if record.supervisor_id else False,
                    }
                )
            else:
                student = self.env["psi.intern.student"].sudo().create(
                    {
                        "name": record.name,
                        "email": record.email,
                        "phone": record.phone,
                        "school": record.school,
                        "field_of_study": record.field_of_study,
                        "required_hours": record.required_hours,
                        "start_date": record.start_date,
                        "end_date": record.end_date,
                        "notes": record.notes,
                        "supervisor_id": record.supervisor_id.id if record.supervisor_id else False,
                        "status": "new",
                    }
                )

            record.student_id = student.id
            record.status = "approved"

    def action_reject(self):
        for record in self:
            record.write(
                {
                    "status": "rejected",
                    "user_id": False,
                }
            )
