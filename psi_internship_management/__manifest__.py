{
    "name": "Zarządzanie praktykantami",
    "version": "18.0.1.0.0",
    "summary": "Moduł do zarządzania praktykami",
    "category": "Zasoby ludzkie",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/intern_student_views.xml",
        "views/intern_attendance_views.xml",
        "views/psi_internship_management_menus.xml",
        ],
    "assets":{
        "web.assets_backend":[
            "psi_internship_management/static/src/css/intern_student_kanban.css",

        ],
    },
    "application": True,
    "installable": True,
}