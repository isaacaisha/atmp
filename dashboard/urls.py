# /home/siisi/atmp/dashboard/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('cards/',               views.CardsView.as_view(),             name='cards'),
    path('charts/',              views.ChartsView.as_view(),            name='charts'),
    path('tables/',              views.TablesView.as_view(),            name='tables'),
    path('buttons/',             views.ButtonsView.as_view(),           name='buttons'),
    path('403/',                 views.Error403View.as_view(),          name='page_403'),
    path('404/',                 views.Error404View.as_view(),          name='page_404'),
    path('blank/',               views.BlankPageView.as_view(),         name='blank_page'),
    path('utilities/colors/',    views.UtilitiesColorView.as_view(),    name='utilities_color'),
    path('utilities/borders/',   views.UtilitiesBorderView.as_view(),   name='utilities_border'),
    path('utilities/animation/', views.UtilitiesAnimView.as_view(),     name='utilities_animation'),
    path('utilities/other/',     views.UtilitiesOtherView.as_view(),    name='utilities_other'),
]
