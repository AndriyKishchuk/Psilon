from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternApplication(models.Model):
    _name = "psi.intern.application"
    _inherit = ["mail.thread", "mail.activity.mixin"]
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

    def _create_supervisor_activity(self, summary, note):
        activity_type = self.env.ref(
            "mail.mail_activity_data_todo",
            raise_if_not_found=False,
        )
        if not activity_type:
            return

        model_id = self.env["ir.model"]._get_id(self._name)
        for record in self:
            if not record.supervisor_id:
                continue

            existing_activity = self.env["mail.activity"].sudo().search(
                [
                    ("res_model_id", "=", model_id),
                    ("res_id", "=", record.id),
                    ("user_id", "=", record.supervisor_id.id),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
            if existing_activity:
                continue

            self.env["mail.activity"].sudo().create(
                {
                    "activity_type_id": activity_type.id,
                    "summary": summary,
                    "note": note,
                    "user_id": record.supervisor_id.id,
                    "res_id": record.id,
                    "res_model_id": model_id,
                }
            )

    def _notify_supervisor_inbox(self, subject, body):
        for record in self:
            partner = record.supervisor_id.partner_id
            if not partner:
                continue

            record.message_post(
                body=body,
                subject=subject,
                partner_ids=[partner.id],
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
            )

    def get_signup_url(self):
        self.ensure_one()
        return "/internship/create-account/%s" % self.registration_token

    def _send_approval_email(self):
        template = self.env.ref(
            "psi_internship_management.mail_template_intern_application_approved",
            raise_if_not_found=False,
        )
        if not template:
            return
        for record in self:
            template.send_mail(record.id, force_send=True)

    def _send_rejection_email(self):
        template = self.env.ref(
            "psi_internship_management.mail_template_intern_application_rejected",
            raise_if_not_found=False,
        )
        if not template:
            return
        for record in self:
            if record.email:
                template.send_mail(record.id, force_send=True)

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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._create_supervisor_activity(
                "Nowe zgloszenie praktykanta",
                "Praktykant %s wyslal nowe zgloszenie. Sprawdz dane i zdecyduj, czy je zaakceptowac."
                % (record.name,),
            )
            record._notify_supervisor_inbox(
                "Nowe zgloszenie praktykanta",
                "Praktykant <b>%s</b> wyslal nowe zgloszenie. Przejdz do zgloszenia i sprawdz jego dane."
                % (record.name,),
            )
        return records

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
            record._send_approval_email()

    def action_reject(self):
        for record in self:
            record.write(
                {
                    "status": "rejected",
                    "user_id": False,
                }
            )
            record._send_rejection_email()

    def action_notify_account_created(self):
        for record in self:
            record._create_supervisor_activity(
                "Praktykant utworzyl konto",
                "Praktykant %s utworzyl konto portalowe i moze juz korzystac ze swojej strefy praktyk."
                % (record.name,),
            )
            record._notify_supervisor_inbox(
                "Praktykant utworzyl konto",
                "Praktykant <b>%s</b> utworzyl konto portalowe i moze juz korzystac ze swojej strefy praktyk."
                % (record.name,),
            )
