"""Build the French report and six-slide PDF from executed results (ReportLab optional)."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from xml.sax.saxutils import escape

import reportlab
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor('#17334A');TEAL=colors.HexColor('#007D83');MUTED=colors.HexColor('#536572')
fontroot=Path('C:/Windows/Fonts')
if (fontroot/'arial.ttf').exists():normal,bold=fontroot/'arial.ttf',fontroot/'arialbd.ttf'
else:normal,bold=Path(reportlab.__file__).parent/'fonts/Vera.ttf',Path(reportlab.__file__).parent/'fonts/VeraBd.ttf'
pdfmetrics.registerFont(TTFont('ReportSans',str(normal)));pdfmetrics.registerFont(TTFont('ReportSansBold',str(bold)))
pdfmetrics.registerFontFamily('ReportSans',normal='ReportSans',bold='ReportSansBold',italic='ReportSans',boldItalic='ReportSansBold')
ST={
 'body':ParagraphStyle('body',fontName='ReportSans',fontSize=10,leading=14.5,textColor=NAVY,spaceAfter=9),
 'small':ParagraphStyle('small',fontName='ReportSans',fontSize=8.3,leading=11.4,textColor=NAVY,spaceAfter=5),
 'title':ParagraphStyle('title',fontName='ReportSansBold',fontSize=27,leading=33,textColor=NAVY,spaceAfter=20),
 'h1':ParagraphStyle('h1',fontName='ReportSansBold',fontSize=20,leading=25,textColor=NAVY,spaceAfter=14,keepWithNext=True),
 'h2':ParagraphStyle('h2',fontName='ReportSansBold',fontSize=13,leading=18,textColor=TEAL,spaceBefore=12,spaceAfter=7,keepWithNext=True),
 'slide':ParagraphStyle('slide',fontName='ReportSans',fontSize=19,leading=28,textColor=NAVY),
 'slideSmall':ParagraphStyle('slideSmall',fontName='ReportSans',fontSize=15,leading=22,textColor=MUTED),
}


def markup(text):
    text=text.replace('—','-').replace('–','-').replace('\u2011','-')
    text=escape(text)
    text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<b>\1</b>',text)
    return re.sub(r'https?://[^\s<]+',lambda m:f'<a href="{m[0]}" color="#007D83">{m[0]}</a>',text)


def md_document(path):
    lines=path.read_text(encoding='utf-8').splitlines();result=[];buffer=[];i=0;code=False
    def flush():
        if buffer:result.append(Paragraph(markup(' '.join(buffer)),ST['small' if code else 'body']));buffer.clear()
    while i<len(lines):
        line=lines[i].strip()
        if line.startswith('```'):flush();code=not code;i+=1;continue
        if line.startswith('|'):
            flush();rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                parts=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',v or '-') for v in parts):rows.append(parts)
                i+=1
            n=max(map(len,rows));widths=[487/n]*n
            if n==4:widths=[145,105,105,132]
            if n==3:widths=[115,115,257]
            if n==3 and rows[0][0]=='Condition':widths=[255,116,116]
            data=[[Paragraph(markup(c),ST['small']) for c in row] for row in rows]
            table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DFECEF')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F4F7F9')]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            result.extend([table,Spacer(1,12)]);continue
        if not line:flush()
        elif code:flush();result.append(Paragraph(markup(line),ST['small']))
        elif line.startswith('# '):flush();result.append(Paragraph(markup(line[2:]),ST['h1']))
        elif line.startswith('## '):flush();result.append(Paragraph(markup(line[3:]),ST['h2']))
        elif line.startswith('- '):flush();result.append(Paragraph('• '+markup(line[2:]),ST['body']))
        elif re.match(r'^\d+\. ',line):flush();result.append(Paragraph(markup(line),ST['body']))
        else:buffer.append(line)
        i+=1
    flush();return result


def footer(c,doc):
    c.saveState();w,h=A4;c.setStrokeColor(TEAL);c.line(54,h-38,w-54,h-38)
    c.setFont('ReportSans',8);c.setFillColor(MUTED);c.drawString(54,h-29,'DÉCLIC / O08 / Phase 6 - validation et livraison')
    c.drawString(54,28,'15 octobre 2026 • Bilan vérifié et limites explicites');c.drawRightString(w-54,28,str(doc.page));c.restoreState()


def report(output,revision,ci_url):
    story=[Paragraph('DÉCLIC • AXE O08',ST['h2']),Paragraph('Phase 6<br/>Validation scientifique,<br/>ingénierie et produit',ST['title']),
           Paragraph('Rapport détaillé pour Melek Moalla - 15 octobre 2026',ST['body']),Spacer(1,12),
           Paragraph('Une réparation de chronologie, 22 entraînements réels, des contrôles plus exigeants et une démonstration sur des parcours de test.',ST['body']),
           Paragraph('<b>Conclusion :</b> intérêt prédictif confirmé dans le benchmark SingPAD corrigé. Les contrôles historiques restent compétitifs ou meilleurs sur AMME et Yousician. Aucun transfert au piano ni bénéfice pédagogique démontré.',ST['body']),Spacer(1,12),
           Paragraph('Le rapport sépare les travaux terminés, les résultats réellement mesurés, les limites et les expériences restant à faire. Les résultats CPU et GPU ne sont pas confondus.',ST['body']),
           Paragraph('Version livrée : '+escape(revision),ST['small']),
           Paragraph('Vérification distante : '+markup(ci_url),ST['small']),Spacer(1,18),
           Paragraph('Contenu : bilan et statuts des jalons ; résultats par découpage et ablations ; dossier scientifique et questions de soutenance ; reproduction et exploitation.',ST['body'])]
    for file in ('PHASE6_REPORT.md','PHASE6_RESULTS.md','PHASE6_SCIENCE_FR.md','PHASE6_REPRODUCTION.md'):
        story.append(PageBreak());story.extend(md_document(ROOT/'docs'/file))
    SimpleDocTemplate(str(output),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=58,bottomMargin=49,
                      title='DÉCLIC Phase 6 - rapport détaillé',author='DÉCLIC - Melek Moalla').build(story,onFirstPage=footer,onLaterPages=footer)


def presentation(output,revision):
    c=canvas.Canvas(str(output),pagesize=(960,540));c.setTitle('DÉCLIC Phase 6 - présentation professeur');c.setAuthor('DÉCLIC - Melek Moalla')
    def para(text,x,y,width=820,style='slide'):
        p=Paragraph(text,ST[style]);_,height=p.wrap(width,450);p.drawOn(c,x,y-height);return y-height
    def slide(number,title,subtitle):
        c.setFillColor(colors.HexColor('#F6F8F7'));c.rect(0,0,960,540,fill=1,stroke=0)
        c.setFillColor(TEAL);c.rect(0,516,960,24,fill=1,stroke=0)
        c.setFillColor(NAVY);c.setFont('ReportSansBold',27);c.drawString(58,464,title)
        para(subtitle,58,433,style='slideSmall')
        c.setFont('ReportSans',10);c.setFillColor(MUTED);c.drawString(58,22,'DÉCLIC / O08 • 15 octobre 2026 • '+revision[:8]);c.drawRightString(905,22,f'{number} / 6')
    slide(1,'De plusieurs séances à une prévision','Le modèle décrit une cible musicale précise, pas une maîtrise générale.')
    y=365
    for text in ['<b>Entrée :</b> résultats antérieurs, concepts de la source et exercice connu.',
                 '<b>Sorties :</b> probabilité ou score futur + bilan des observations + signal descriptif de fragilité.',
                 '<b>Preuve :</b> un vrai parcours de test, absent de l’entraînement ; résultat futur caché puis révélé.']:
        y=para(text,70,y)-28
    c.showPage()
    slide(2,'Trois bases, trois tâches','Les cibles et les instruments restent séparés.')
    y=365
    for text in ['<b>AMME / clavier :</b> prochain bloc de score mélodique continu. Petit échantillon : recherche seulement.',
                 '<b>SingPAD / chant :</b> réussite de notes par concept du prochain groupe d’enregistrements.',
                 '<b>Yousician / ukulélé :</b> fraction de notes et accords réussis au prochain jour actif.']:
        y=para(text,70,y)-27
    c.showPage()
    slide(3,'La correction avant la complexité','La Phase 5 classait certaines dates comme du texte.')
    para('<b>340 parcours affectés ; 478 inversions.</b><br/><br/>Dates analysées, égalités regroupées, originaux conservés.<br/><br/><b>0 inversion sur 18 328 groupes reconstruits.</b><br/><br/>Anciens caches et modèles invalidés ; DKT-GRU, EnhancedGRU et attention réentraînés depuis zéro.',70,365)
    c.showPage()
    slide(4,'Ce que les expériences montrent','Trois découpages CPU prédéfinis ; cinq contrôles historiques ; quatre ablations.')
    y=365
    for text in ['<b>SingPAD :</b> log-loss moyenne réseau 0,518 ; contrôle historique 0,541. Plus faible est préférable.',
                 '<b>Yousician :</b> MAE réseau 9,15 points ; contrôle 8,98 points. La méthode simple est légèrement meilleure.',
                 '<b>AMME :</b> résultats instables et peu de cibles. Aucun gain général annoncé.']:
        y=para(text,70,y)-22
    para('Bootstrap par apprenant entier. Aucune note traitée comme un élève indépendant. Les ablations ne prouvent pas l’utilité de chaque composant.',70,105,style='slideSmall')
    c.showPage()
    slide(5,'Une démonstration honnête et reproductible','Le passé, la prévision, puis seulement le résultat réel.')
    y=365
    for text in ['Le graphe montre les résultats déjà observés ; les probabilités portent sur les concepts définis.',
                 '« Non évalué » et « preuve insuffisante » restent visibles. Une mauvaise séance n’est pas un diagnostic.',
                 'Un signal récurrent exige plusieurs groupes et assez de notes. La règle est explicite, pas pédagogiquement validée.']:
        y=para(text,70,y)-24
    c.showPage()
    slide(6,'Ce qui est établi, ce qui reste à valider','Des résultats scientifiques défendables comprennent aussi les résultats négatifs.')
    y=365
    for text in ['<b>Établi :</b> chronologie corrigée, entraînements exécutés, modèles intégrés, contrôles, reprise et tests.',
                 '<b>Non établi :</b> maîtrise cognitive, gain pédagogique, confiance individuelle, transfert automatique au piano.',
                 '<b>Suite :</b> confirmer les ablations, étudier les données manquantes, construire avec l’enseignant une vraie évaluation piano prospective.']:
        y=para(text,70,y)-25
    c.showPage();c.save()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True);parser.add_argument('--ci-url',default='Contrôle de livraison en cours')
    args=parser.parse_args();destination=Path(args.output);destination.mkdir(parents=True,exist_ok=True)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report(destination/'DECLIC_Phase6_Rapport_detaille.pdf',revision,args.ci_url)
    presentation(destination/'DECLIC_Phase6_Presentation_professeur.pdf',revision)
    print(json.dumps({'report':str(destination/'DECLIC_Phase6_Rapport_detaille.pdf'),'presentation':str(destination/'DECLIC_Phase6_Presentation_professeur.pdf')}))
