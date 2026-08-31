import streamlit as st
from config import settings


def inject_analytics():
    """
    Injeta os scripts de rastreamento (GA4 e Meta Pixel) no cabeçalho do app.
    Deve ser chamado logo no início do app.py.
    """

    # 1. Google Analytics 4 (GA4)
    if settings.GA_TRACKING_ID:
        ga_code = f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={settings.GA_TRACKING_ID}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{settings.GA_TRACKING_ID}');
        </script>
        """
        # Injeta sem ocupar espaço visual
        st.markdown(ga_code, unsafe_allow_html=True)

    # 2. Meta Pixel (Facebook/Instagram Ads)
    if settings.META_PIXEL_ID:
        pixel_code = f"""
        <script>
        !function(f,b,e,v,n,t,s)
        {{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
        n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
        if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
        n.queue=[];t=b.createElement(e);t.async=!0;
        t.src=v;s=b.getElementsByTagName(e)[0];
        s.parentNode.insertBefore(t,s)}}(window, document,'script',
        'https://connect.facebook.net/en_US/fbevents.js');
        fbq('init', '{settings.META_PIXEL_ID}');
        fbq('track', 'PageView');
        </script>
        <noscript><img height="1" width="1" style="display:none"
        src="https://www.facebook.com/tr?id={settings.META_PIXEL_ID}&ev=PageView&noscript=1"
        /></noscript>
        """
        st.markdown(pixel_code, unsafe_allow_html=True)


def track_event(event_name, details={}):
    """
    Dispara um evento específico (ex: 'Purchase', 'Lead', 'Search').
    Útil para saber quando alguém clica em 'Pagar'.
    """
    if settings.META_PIXEL_ID:
        script = f"<script>fbq('track', '{event_name}');</script>"
        st.markdown(script, unsafe_allow_html=True)
