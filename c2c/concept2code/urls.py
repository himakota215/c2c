from django.urls import path
from .views import (
    login_page,
    register_page,
    register,
    login_api,
    logout_api,
    dashboard,
    session_check,
    level_list,
    topic_list,
    task_list,
    task_detail,
    submit_code,
    generate_code
)

urlpatterns = [

    # Pages
    path('login/', login_page),
    path('register/', register_page),
    path('dashboard/', dashboard),
    path('levels/', level_list),
    path('levels/<int:level_id>/topics/', topic_list),
    path('topics/<int:topic_id>/tasks/', task_list),
    path('tasks/<int:task_id>/', task_detail),

    # APIs
    path('api/register/', register),
    path('api/login/', login_api),
    path('api/logout/', logout_api),
    path('api/session/', session_check),
    path('api/submit-code/', submit_code),

    # AI
    path('api/generate-code/', generate_code),
]