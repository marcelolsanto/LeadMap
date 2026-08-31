var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (document.documentElement.lang !== 'pt-BR') {
            document.documentElement.lang = 'pt-BR';
        }
    });
});
observer.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
document.documentElement.lang = 'pt-BR';

var audio = new Audio('https://www.soundjay.com/buttons/sounds/button-3.mp3');
function playClick() { audio.currentTime = 0; audio.play(); }
document.addEventListener('DOMContentLoaded', function() {
    document.body.addEventListener('click', function(e) {
        if (e.target.closest('button') || e.target.closest('.lead-card') || e.target.closest('.google-btn')) {
            playClick();
        }
    });
});

// No seu HTML/JS
document.getElementById('meu-botao').addEventListener('click', function() {
    fetch('/api/track-event/', {
        method: 'POST',
        body: JSON.stringify({ event: 'clique_botao_vendas', timestamp: new Date() })
    });
});
