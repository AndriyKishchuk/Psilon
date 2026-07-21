from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternApplication(models.Model):
    _name = "psi.intern.application"
    _description = "Internship Application"
    _order = "create_date desc"

    name = fields.Char(string="Imię i nazwisko", required=True)
    email = fields.Char(string="Email", required=True)
    phone = fields.Char(string="Telefon", required=True)
    school = fields.Char(string="Szkoła / Uczelnia", required=True)
    field_of_study = fields.Char(string="Kierunek/Profil", required=True)
    required_hours = fields.Integer(string="Wymagana liczba godzin", required=True)
    start_date = fields.Date(string="Data rozpoczęcia")
    end_date = fields.Date(string="Data zakończenia")
    notes = fields.Text(string="Notatka")
    supervisor_id = fields.Many2one("res.users", string="Opiekun")
    registration_token = fields.Char(string="Token rejestracji", copy=False)
    user_id = fields.Many2one("res.users", string="Użytkownik", ondelete="set null")
    student_id = fields.Many2one("psi.intern.student", string="Praktykant", ondelete="cascade")
    password_plain = fields.Char(string="Hasło tymczasowe")
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

    @api.constrains("required_hours")
    def _check_required_hours(self):
        for record in self:
            if record.required_hours <= 0:
                raise ValidationError("Wymagana liczba godzin musi być większa od zera.")

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError("Data zakonczenia nie moze byc wczesniejsza niz data rozpoczęcia.")

    def action_approve(self):
        portal_group = self.env.ref("base.group_portal")

        for record in self:
            if record.status != "new":
                continue

            user = record.user_id.sudo() if record.user_id else self.env["res.users"].sudo()
            if not record.user_id:
                existing_user = self.env["res.users"].sudo().search(
                    [("login", "=", record.email)],
                    limit=1,
                )
                if existing_user:
                    existing_student = self.env["psi.intern.student"].sudo().search(
                        [("user_id", "=", existing_user.id)],
                        limit=1,
                    )
                    if existing_student and existing_student.id != record.student_id.id:
                        raise ValidationError("Istnieje już praktykant powiązany z tym adresem e-mail.")
                    user = existing_user
                    user.write(
                        {
                            "active": True,
                            "name": record.name,
                            "login": record.email,
                            "email": record.email,
                            "phone": record.phone,
                            "groups_id": [(4, portal_group.id)],
                        }
                    )
                    if record.password_plain:
                        user.write({"password": record.password_plain})
                else:
                    user = self.env["res.users"].sudo().create(
                        {
                            "name": record.name,
                            "login": record.email,
                            "email": record.email,
                            "password": record.password_plain or "intern123",
                            "groups_id": [(6, 0, [portal_group.id])],
                        }
                    )
            else:
                user.write(
                    {
                        "name": record.name,
                        "login": record.email,
                        "email": record.email,
                        "phone": record.phone,
                        "groups_id": [(4, portal_group.id)],
                    }
                )
                if record.password_plain:
                    user.write({"password": record.password_plain})

            if user.partner_id:
                user.partner_id.sudo().write(
                    {
                        "name": record.name,
                        "email": record.email,
                        "phone": record.phone,
                    }
                )

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
                        "user_id": user.id,
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
                        "user_id": user.id,
                        "status": "new",
                    }
                )

            record.user_id = user.id
            record.student_id = student.id
            record.status = "approved"

    def action_reject(self):
        for record in self:
            user = record.user_id.sudo()
            record.write(
                {
                    "status": "rejected",
                    "user_id": False,
                }
            )
            if user:
                user.unlink()
