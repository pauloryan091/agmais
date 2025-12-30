// header.js - Sistema de Header Unificado e Responsivo
function loadHeader() {
    // Verificar se já existe um header
    if (document.querySelector('header')) {
        initHeader();
        return;
    }
    
    // Criar elemento header
    const header = document.createElement('header');
    header.innerHTML = `
        <div class="header-content">
            <a href="index.html" class="logo">Agendamento+</a>
            <button id="menuBtn" aria-label="Abrir menu" aria-expanded="false">☰</button>
            <nav id="menu" class="nav-links" aria-label="Navegação principal">
                <a href="dashboard.html" class="nav-link">Dashboard</a>
                <a href="serviços.html" class="nav-link">Serviços</a>
                <a href="clientes.html" class="nav-link">Clientes</a>
                <a href="agendamento.html" class="nav-link">Agendamentos</a>
                <a href="perfil.html" class="nav-link">Perfil</a>
            </nav>
            <button id="themeToggle" class="theme-toggle" aria-label="Alternar tema">
                <span class="theme-text">Tema Escuro</span>
            </button>
        </div>
    `;
    
    // Inserir o header no início do body
    document.body.insertBefore(header, document.body.firstChild);
    
    initHeader();
}

function initHeader() {
    const menuBtn = document.getElementById('menuBtn');
    const menu = document.getElementById('menu');
    const themeToggle = document.getElementById('themeToggle');
    
    // =====================
    // CONTROLE DO MENU MOBILE
    // =====================
    if (menuBtn && menu) {
        const toggleMenu = () => {
            const isOpen = menu.classList.contains('show');
            menu.classList.toggle('show');
            menuBtn.classList.toggle('active');
            menuBtn.setAttribute('aria-expanded', !isOpen);
            menuBtn.innerHTML = isOpen ? '☰' : '✕';
            
            // Prevenir scroll quando menu está aberto
            if (!isOpen) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
        };
        
        menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMenu();
        });
        
        // Fechar menu ao clicar em um link (mobile)
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 767) {
                    menu.classList.remove('show');
                    menuBtn.classList.remove('active');
                    menuBtn.setAttribute('aria-expanded', 'false');
                    menuBtn.innerHTML = '☰';
                    document.body.style.overflow = '';
                }
            });
        });
        
        // Fechar menu ao clicar fora (mobile)
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 767 && 
                menu.classList.contains('show') && 
                !menu.contains(e.target) && 
                !menuBtn.contains(e.target)) {
                menu.classList.remove('show');
                menuBtn.classList.remove('active');
                menuBtn.setAttribute('aria-expanded', 'false');
                menuBtn.innerHTML = '☰';
                document.body.style.overflow = '';
            }
        });
        
        // Fechar menu ao redimensionar para desktop
        window.addEventListener('resize', () => {
            if (window.innerWidth > 767) {
                menu.classList.remove('show');
                menuBtn.classList.remove('active');
                menuBtn.setAttribute('aria-expanded', 'false');
                menuBtn.innerHTML = '☰';
                document.body.style.overflow = '';
            }
        });
        
        // Fechar menu com tecla ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && menu.classList.contains('show')) {
                menu.classList.remove('show');
                menuBtn.classList.remove('active');
                menuBtn.setAttribute('aria-expanded', 'false');
                menuBtn.innerHTML = '☰';
                document.body.style.overflow = '';
            }
        });
    }
    
    // =====================
    // CONTROLE DO TEMA CLARO/ESCURO
    // =====================
    if (themeToggle) {
        // Verificar tema salvo no localStorage
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeButton(savedTheme);
        
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeButton(newTheme);
        });
    }
    
    // Marcar link ativo
    highlightActiveLink();
    
    // Adicionar listener para mudanças de página
    window.addEventListener('pageshow', highlightActiveLink);
}

function updateThemeButton(theme) {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const themeText = themeToggle.querySelector('.theme-text');
        if (themeText) {
            themeText.textContent = theme === 'light' ? 'Tema Escuro' : 'Tema Claro';
        } else {
            themeToggle.textContent = theme === 'light' ? 'Tema Escuro' : 'Tema Claro';
        }
        themeToggle.setAttribute('aria-label', theme === 'light' ? 'Alternar para tema escuro' : 'Alternar para tema claro');
    }
}

function highlightActiveLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        const linkHref = link.getAttribute('href');
        
        // Verificar correspondência exata
        if (linkHref === currentPage) {
            link.classList.add('active');
        }
        
        // Tratamento para página inicial
        if ((currentPage === '' || currentPage === 'index.html') && linkHref === 'index.html') {
            link.classList.add('active');
        }
        
        // Tratamento para páginas sem extensão .html
        if (linkHref && linkHref.replace('.html', '') === currentPage.replace('.html', '')) {
            link.classList.add('active');
        }
    });
}

// Carregar o header quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadHeader);
} else {
    loadHeader();
}

// Exportar função para uso global
window.alternarTema = function() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
};