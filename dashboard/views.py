# /home/siisi/atmp/dashboard/views.py

from django.views.generic import TemplateView
from django.shortcuts import render

def custom_permission_denied_view(request, exception=None):
    return render(request, 'dashboard/403.html', status=403)

def custom_page_not_found_view(request, exception=None):
    return render(request, 'dashboard/404.html', status=404)


class CardsView(TemplateView):
    template_name = 'dashboard/cards.html'

class ChartsView(TemplateView):
    template_name = 'dashboard/charts.html'

class TablesView(TemplateView):
    template_name = 'dashboard/tables.html'

class ButtonsView(TemplateView):
    template_name = 'dashboard/buttons.html'

class BlankPageView(TemplateView):
    template_name = 'dashboard/blank.html'

class Error403View(TemplateView):
    # You generally set this in handler404, but if you want a standalone:
    template_name = 'dashboard/403.html'

class Error404View(TemplateView):
    template_name = 'dashboard/404.html'

class UtilitiesColorView(TemplateView):
    template_name = 'dashboard/utilities-color.html'

class UtilitiesBorderView(TemplateView):
    template_name = 'dashboard/utilities-border.html'

class UtilitiesAnimView(TemplateView):
    template_name = 'dashboard/utilities-animation.html'

class UtilitiesOtherView(TemplateView):
    template_name = 'dashboard/utilities-other.html'
