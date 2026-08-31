# Arquivo: modules/stealth.py

def stealth_sync(page):
    """
    Injeta scripts para esconder que o navegador é um robô.
    Substitui a biblioteca 'playwright-stealth'.
    """
    # 1. Remove a propriedade 'webdriver' (O maior delator)
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    # 2. Finge ter plugins (Chrome real tem, robôs não)
    page.add_init_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    """)

    # 3. Finge ser um Chrome padrão
    page.add_init_script("""
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
    """)

    # 4. Ajusta permissões
    page.add_init_script("""
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
    """)

    # 5. Idiomas
    page.add_init_script("""
        Object.defineProperty(navigator, 'languages', {
            get: () => ['pt-BR', 'pt', 'en-US', 'en']
        });
    """)
