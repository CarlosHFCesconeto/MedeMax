"""Project identity and supplied team credits. No acquisition dependencies."""
from html import escape
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
from .branding import asset_path, logo

MEMBERS = (
    ('Alessandro da Silva Ribeiro', 'Graduando • 2026', 'alessandroribeiroalessandro84@gmail.com'),
    ('Arthur Marques dos Santos', 'Graduando • 2026', 'arthurmarquesdossantos@gmail.com'),
    ('Breno Elias Bretas de Carvalho', 'Professor do Centro Universitário UniSATC', 'breno.carvalho@satc.edu.br'),
    ('Carlos Henrique Fernandes Cesconeto', 'Graduando • 2026', 'carloshcesconeto@gmail.com'),
    ('Guilherme Bernardino Eufrasio', 'Graduando • 2026', 'engguilhermebernardino@gmail.com'),
    ('João Luís Rosso Izidoro', 'Graduando • 2026', 'jluisizidoro@gmail.com'),
    ('Leonardo Mariano Kunen', 'Graduando • 2026', 'leo.marianok@gmail.com'),
    ('Vitor Rodrigues Pizzetti', 'Graduando • 2026', 'vitorpizzetti@gmail.com'),
)


def text(value, style=''):
    label = QLabel(value)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    label.setStyleSheet('background:transparent;' + style)
    return label


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addWidget(text('Sobre', 'font-size:25px;font-weight:600;'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 12, 0)
        body.setSpacing(18)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        hero = QFrame()
        hero.setObjectName('aboutHero')
        hero.setStyleSheet('QFrame#aboutHero{background:#111827;border-radius:12px;}')
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(22, 18, 28, 18)
        hero_row.addWidget(logo('medemax.png', 190, 190, 'Logo do projeto MedeMax'))
        intro = QVBoxLayout()
        intro.addWidget(text('PROJETO ACADÊMICO', 'color:#fb923c;font-size:12px;font-weight:700;'))
        intro.addWidget(text('MedeMax', 'color:white;font-size:34px;font-weight:700;'))
        intro.addWidget(text('Monitoramento e supervisão Modbus', 'color:#e2e8f0;font-size:17px;'))
        intro.addWidget(text('Aquisição, visualização e histórico de dados para apoiar o trabalho com equipamentos e sistemas de engenharia.', 'color:#cbd5e1;font-size:14px;'))
        intro.addStretch()
        hero_row.addLayout(intro, 1)
        body.addWidget(hero)

        group = QFrame()
        group.setObjectName('groupCard')
        group.setStyleSheet('QFrame#groupCard{background:white;border:1px solid #dce3eb;border-radius:10px;}')
        row = QHBoxLayout(group)
        row.setContentsMargins(18, 16, 22, 16)
        logo_panel = QFrame()
        logo_panel.setObjectName('groupLogo')
        logo_panel.setStyleSheet('QFrame#groupLogo{background:#111827;border-radius:8px;}')
        logo_layout = QVBoxLayout(logo_panel)
        logo_layout.addWidget(logo('grupo_maxwell.png', 165, 145, 'Logo do Grupo Maxwell'))
        row.addWidget(logo_panel)
        description = QVBoxLayout()
        description.addWidget(text('Quem somos', 'font-size:20px;font-weight:600;'))
        description.addWidget(text('Somos o Grupo Maxwell, um grupo de estudantes da UniSATC que desenvolve o MedeMax como projeto acadêmico de engenharia.', 'font-size:14px;'))
        description.addWidget(text('Nosso objetivo é construir uma ferramenta simples e ágil para aquisição de dados, monitoramento e supervisão de equipamentos via Modbus RTU e TCP.', 'color:#475569;font-size:14px;'))
        row.addLayout(description, 1)
        body.addWidget(group)

        body.addWidget(text('Equipe do projeto', 'font-size:21px;font-weight:600;'))
        for name, role, email in MEMBERS:
            card = QFrame()
            card.setObjectName('memberCard')
            card.setStyleSheet('QFrame#memberCard{background:white;border:1px solid #dce3eb;border-radius:7px;}')
            layout = QVBoxLayout(card)
            layout.setContentsMargins(16, 12, 16, 12)
            layout.setSpacing(4)
            layout.addWidget(text(name, 'font-size:15px;font-weight:600;'))
            layout.addWidget(text(role, 'color:#64748b;'))
            contact = QLabel(f'<a style="color:#2563eb" href="mailto:{escape(email, quote=True)}">{escape(email)}</a>')
            contact.setWordWrap(True)
            contact.setStyleSheet('background:transparent;')
            contact.setTextInteractionFlags(Qt.TextBrowserInteraction)
            contact.setOpenExternalLinks(True)
            layout.addWidget(contact)
            body.addWidget(card)

        institution = QFrame()
        institution.setObjectName('institutionCard')
        institution.setStyleSheet('QFrame#institutionCard{background:#eaf0f7;border-radius:8px;}')
        institution_row = QHBoxLayout(institution)
        institution_row.setContentsMargins(18, 16, 18, 16)
        caption = QVBoxLayout()
        caption.addWidget(text('Instituição de ensino', 'color:#64748b;font-size:12px;'))
        caption.addWidget(text('Centro Universitário UniSATC', 'font-size:17px;font-weight:600;'))
        institution_row.addLayout(caption, 1)
        self.institution_logo = None
        if asset_path('logosatc.png'):
            self.institution_logo = logo('logosatc.png', 180, 90, 'Logo da UniSATC')
            institution_row.addWidget(self.institution_logo)
        body.addWidget(institution)
        body.addWidget(text('MedeMax • Versão 0.3.6 • Grupo Maxwell • 2026', 'color:#64748b;font-size:12px;'))
        body.addStretch()
