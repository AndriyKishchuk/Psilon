from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternAttendance(models.Model):
    _name = "psi.intern.attendance"
    _description = "Intern Attendance Plan"
    _order = "start_datetime desc"

    intern_id = fields.Many2one(
        "psi.intern.student",
        string="Praktykant",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one("res.users", string="Uzytkownik systemu")
    start_datetime = fields.Datetime(string="Data i godzina rozpoczecia", required=True)
    end_datetime = fields.Datetime(string="Data i godzina zakonczenia")
    supervisor_id = fields.Many2one(
        "res.users",
        string="Opiekun",
        related="intern_id.supervisor_id",
        store=True,
        readonly=True,
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

    duration_hours = fields.Float(
        string="Liczba godzin",
        compute="_compute_duration_hours",
        store=True,
    )

    note = fields.Text(string="Notatka")

    @api.constrains("start_datetime", "end_datetime")
    def _check_attendance_dates(self):
        for record in self:
            if record.start_datetime and record.end_datetime and record.end_datetime <= record.start_datetime:
                raise ValidationError(
                    "Data zakonczenia musi byc pozniejsza niz data rozpoczecia."
                )

    @api.depends("start_datetime", "end_datetime")
    def _compute_duration_hours(self):
        for record in self:
            if record.start_datetime and record.end_datetime and record.end_datetime > record.start_datetime:
                delta = record.end_datetime - record.start_datetime
                record.duration_hours = delta.total_seconds() / 3600.0
            else:
                record.duration_hours = 0.0

    def action_view_student_attendances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Obecnosci praktykanta",
            "res_model": "psi.intern.attendance",
            "view_mode": "list,form",
            "domain": [("intern_id", "=", self.intern_id.id)],
            "context": {
                "default_intern_id": self.intern_id.id,
            },
        }

    @api.onchange("start_datetime", "end_datetime")
    def _onchange_status_from_datetimes(self):
        now = fields.Datetime.now()
        for record in self:
            if record.status == "cancelled":
                continue
            if not record.start_datetime:
                record.status = "new"
            elif record.start_datetime and record.end_datetime:
                if now < record.start_datetime:
                    record.status = "new"
                elif record.start_datetime <= now <= record.end_datetime:
                    record.status = "active"
                elif now > record.end_datetime:
                    record.status = "finished"
            elif record.start_datetime and not record.end_datetime:
                if now < record.start_datetime:
                    record.status = "new"
                else:
                    record.status = "active"

    def _set_status_from_datetimes(self):
        now = fields.Datetime.now()
        for record in self:
            if record.status == "cancelled":
                continue
            if not record.start_datetime:
                record.status = "new"
            elif record.start_datetime and record.end_datetime:
                if now < record.start_datetime:
                    record.status = "new"
                elif record.start_datetime <= now <= record.end_datetime:
                    record.status = "active"
                elif now > record.end_datetime:
                    record.status = "finished"
            elif record.start_datetime and not record.end_datetime:
                if now < record.start_datetime:
                    record.status = "new"
                else:
                    record.status = "active"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._set_status_from_datetimes()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "start_datetime" in vals or "end_datetime" in vals:
            self._set_status_from_datetimes()
        return res
