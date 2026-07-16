from odoo import fields, models

class InternLanguage(models.Model):
    _name = "psi.intern.language"
    _description="Intern Language"
    _order ="language"
    
    intern_id = fields.Many2one(
        "psi.intern.student",
        string="Intern",
        required = True,
        ondelete="cascade"
    )
    language = fields.Selection(
        [
            ("polish", "Polish"),
            ("english", "English"),
            ("ukrainian", "Ukrainian"),
            ("german", "German"),
            ("spanish", "Spanish"),
            ("french", "French"),
        ],
        string="Language",
        required=True,
    )
    level = fields.Selection(
        [
            ("a1", "A1"),
            ("a2", "A2"),
            ("b1", "B1"),
            ("b2", "B2"),
            ("c1", "C1"),
            ("c2", "C2"),
        ],
        string="Level",
        required=True,
    )