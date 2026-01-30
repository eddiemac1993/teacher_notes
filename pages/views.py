from django.shortcuts import render

def about(request):
    return render(request, "pages/about.html")
    
def privacy(request):
    return render(request, "pages/privacy.html")

def teacher_guidelines(request):
    return render(request, "pages/teacher_guidelines.html")

def support(request):
    return render(request, "pages/support.html")
