"""French evidence report and six-slide defense PDF; optional ReportLab runtime."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak,Table,TableStyle,KeepTogether
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
from build_phase6_documents import ST,markup,md_document,NAVY,TEAL,MUTED

ROOT=Path(__file__).resolve().parents[1]


class Report(SimpleDocTemplate):
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name=='h1':
            self._chapter_counter=getattr(self,'_chapter_counter',0)+1
            key=f'chapter-{self._chapter_counter}'
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,level=0,closed=False)


def footer(c,doc):
    c.saveState();w,h=A4;c.setStrokeColor(TEAL);c.line(54,h-38,w-54,h-38)
    c.setFont('ReportSans',8);c.setFillColor(MUTED)
    c.drawString(54,h-29,'DÉCLIC / O08 / Phase 7 - preuves, produit et validation à poursuivre')
    c.drawString(54,28,datetime.now().strftime('%d/%m/%Y')+' - Résultats exécutés et limites explicites')
    c.drawRightString(w-54,28,str(doc.page));c.restoreState()


def flow():
    d=Drawing(487,115)
    entries=[('1. Historique réel','Résultats déjà disponibles'),('2. Réseau entraîné','Prévision sans cible future'),('3. Révélation','Comparer sans cacher l’erreur')]
    for i,(title,subtitle) in enumerate(entries):
        x=i*164
        d.add(Rect(x,30,153,68,rx=9,fillColor=colors.HexColor('#EAF0E9'),strokeColor=colors.HexColor('#B9CDBD')))
        d.add(String(x+10,74,title,fontName='ReportSansBold',fontSize=11,fillColor=NAVY))
        d.add(String(x+10,53,subtitle,fontName='ReportSans',fontSize=8,fillColor=MUTED))
        if i<2:
            d.add(Line(x+154,64,x+163,64,strokeColor=TEAL,strokeWidth=1.5))
    d.add(String(0,10,'États descriptifs et suggestions restent séparés de la prévision statistique.',fontName='ReportSans',fontSize=9,fillColor=MUTED))
    return d


def report(output,revision,ci_url,screenshots):
    data=json.loads((ROOT/'artifacts/phase7/summary.json').read_text(encoding='utf-8'))
    story=[Paragraph('DÉCLIC / OBJECTIF O08',ST['h2']),
        Paragraph('Phase 7<br/>Du passé musical<br/>à une prévision vérifiable',ST['title']),
        Paragraph('Rapport scientifique et technique détaillé - Melek Moalla',ST['body']),
        Paragraph(datetime.now().strftime('%d/%m/%Y'),ST['small']),Spacer(1,12),
        Paragraph('<b>36 entraînements neuronaux terminés.</b> Contrôles appris, ablations, calibration, collecte prospective locale et démonstration sur de vrais parcours de test.',ST['body']),
        Paragraph('<b>Résultat :</b> avantage exploratoire modeste sur SingPAD ; absence de supériorité moyenne convaincante sur AMME et Yousician. Aucun transfert piano ni bénéfice pédagogique démontré.',ST['body']),
        Paragraph('<b>Statut :</b> livraison technique et scientifique substantielle ; validation terrain, taxonomie experte et efficacité des recommandations restent incomplètes.',ST['body']),flow(),
        Paragraph('Branche : phase7/personalized-musical-learning',ST['small']),
        Paragraph('Révision livrée : '+escape(revision),ST['small']),
        Paragraph('CI vérifiée : '+markup(ci_url),ST['small']),
        Paragraph('Lecture : bilan et méthode ; figures ; résultats détaillés ; reproduction ; guide de démonstration ; oral ; Q&amp;A ; résumé anglais ; vérifications.',ST['small'])]
    for name in ['PHASE7_REPORT.md']:
        story.append(PageBreak())
        body=ST['body'].clone('report-body',leading=14,spaceAfter=7)
        story.extend(Paragraph(p.text,body) if isinstance(p,Paragraph) and p.style.name=='body' else p for p in md_document(ROOT/'docs'/name))
    story.append(PageBreak());story.append(Paragraph('Figures issues des résultats exécutés',ST['h1']))
    captions=[('representations-singpad.png','Chaque point est un score de test réellement mesuré. La moyenne est descriptive ; aucun intervalle individuel n’est ajouté.'),
        ('calibration-singpad.png','GRU graine 42 : fréquences de test comparées aux probabilités. Le recalibrage est ajusté sur validation uniquement.'),
        ('missing-history-singpad.png','Modèle gelé et labels cibles inchangés. Les données manquantes sont un stress artificiel explicite.')]
    for index,(name,caption) in enumerate(captions):
        path=ROOT/'artifacts/phase7/figures'/name
        image=Image(str(path));image.drawHeight=487*image.imageHeight/image.imageWidth;image.drawWidth=487
        if index:story.append(PageBreak())
        story.extend([image,Spacer(1,10),Paragraph(caption,ST['body'])])
    if screenshots:
        story.append(PageBreak());story.append(Paragraph('L’application réellement inspectée',ST['h1']))
        for path in screenshots:
            image=Image(str(path));width=487;height=width*image.imageHeight/image.imageWidth
            if height>570:width*=570/height;height=570
            image.drawWidth=width;image.drawHeight=height
            story.extend([image,Spacer(1,8),Paragraph('Capture réelle de la démonstration locale. Les résultats futurs sont révélés après le calcul ; les erreurs ne sont pas masquées.',ST['small']),PageBreak()])
    for name in ['PHASE7_RESULTS.md','PHASE7_REPRODUCTION.md','PHASE7_DEMO_GUIDE.md','PHASE7_PRESENTATION_FR.md','PHASE7_QA_FR.md','PHASE7_EXECUTIVE_SUMMARY_EN.md','PHASE7_VERIFICATION.md']:
        if story and not isinstance(story[-1],PageBreak):story.append(PageBreak())
        content=md_document(ROOT/'docs'/name)
        if name in ('PHASE7_PRESENTATION_FR.md','PHASE7_VERIFICATION.md'):
            compact=ST['body'].clone('compact-appendix-body',fontSize=9.6,leading=13.4,spaceAfter=7)
            content=[Paragraph(p.text,compact) if isinstance(p,Paragraph) and p.style.name=='body' else p for p in content]
        story.extend(content)
    Report(str(output),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=58,bottomMargin=49,
        title='DÉCLIC Phase 7 - rapport scientifique et technique',author='DÉCLIC - Melek Moalla').build(story,onFirstPage=footer,onLaterPages=footer)


def slides(output,revision):
    c=canvas.Canvas(str(output),pagesize=(960,540));c.setTitle('DÉCLIC Phase 7 - soutenance cinq minutes')
    c.setAuthor('Melek Moalla / DÉCLIC')
    def paragraph(text,x,y,width=810,style='slide'):
        p=Paragraph(text,ST[style]);_,height=p.wrap(width,450);p.drawOn(c,x,y-height);return y-height
    def slide(number,title,subtitle):
        c.setFillColor(colors.HexColor('#F5F5EE'));c.rect(0,0,960,540,fill=1,stroke=0)
        c.setFillColor(TEAL);c.rect(0,517,960,23,fill=1,stroke=0)
        c.setFont('ReportSansBold',27);c.setFillColor(NAVY);c.drawString(55,465,title)
        paragraph(subtitle,55,431,style='slideSmall')
        c.setFont('ReportSans',10);c.setFillColor(MUTED);c.drawString(55,22,'DÉCLIC / O08 / Phase 7 - '+revision[:8]);c.drawRightString(905,22,f'{number} / 6')
    slide(1,'Prévoir à partir de plusieurs séances','O08 : observations, fragilités et prochaine performance restent distinctes.')
    y=365
    for text in ['<b>Le passé :</b> résultats réellement évalués dans plusieurs groupes.',
        '<b>Le Deep Learning :</b> un GRU traite la suite et prévoit une cible future.',
        '<b>La preuve :</b> résultat caché, vraie prévision, puis révélation et erreur visible.']:
        y=paragraph(text,70,y)-28
    c.showPage()
    slide(2,'Trois bases, trois cibles musicales','Les concepts de chant ne deviennent pas automatiquement des compétences piano.')
    y=365
    for text in ['<b>SingPAD / chant :</b> 1 042 apprenants, 18 328 groupes ; réussite de notes par concept.',
        '<b>Yousician / ukulélé :</b> 999 apprenants ; score du prochain jour actif.',
        '<b>AMME / clavier :</b> 59 apprenants ; similarité mélodique du prochain bloc. Recherche seulement.']:
        y=paragraph(text,70,y)-26
    c.showPage()
    slide(3,'Tester ce que le réseau apporte réellement','36 nouveaux entraînements CPU ; choix des paramètres sur validation uniquement.')
    y=365
    for text in ['<b>Trois splits par apprenant :</b> passé strict, cibles et partitions vérifiées.',
        '<b>Comparer :</b> ordre, fenêtre récente, embeddings, intervalles ; vrais contrôles appris.',
        '<b>Mettre à l’épreuve :</b> passé manquant, calibration et CV groupée AMME.']:
        y=paragraph(text,70,y)-26
    c.showPage()
    slide(4,'Un gain modeste et des résultats négatifs utiles','Moyennes des réseaux et contrôles choisis sur validation, programme principal.')
    y=365
    for text in ['<b>SingPAD, log-loss :</b> réseau 0,517925 / contrôle 0,524188.',
        '<b>Yousician, MAE :</b> réseau 0,090890 / contrôle 0,090296.',
        '<b>AMME, MAE :</b> réseau 0,186280 / contrôle 0,172455.',
        '<b>Pas de promesse universelle :</b> métadonnées Yousician et calibration ne gagnent pas toujours.']:
        y=paragraph(text,70,y)-19
    c.showPage()
    slide(5,'La démonstration : regarder aussi l’erreur','Premier exemple de test éligible, choisi sans regarder sa performance.')
    y=365
    for text in ['<b>1.</b> Lire les résultats passés et les observations insuffisantes.',
        '<b>2.</b> Lancer le vrai réseau, puis révéler le résultat tenu à l’écart.',
        '<b>3.</b> Concept 15 : environ 85,5 % prévus, 40 % observés ; erreur conservée.',
        '<b>4.</b> Suggérer seulement un exercice connu et lié au concept observé.']:
        y=paragraph(text,70,y)-19
    c.showPage()
    slide(6,'Le prochain progrès doit venir du terrain','La mécanique est livrée ; la validation pédagogique reste à construire.')
    y=365
    for text in ['<b>Prêt techniquement :</b> événements pseudonymes, consentement, prévisions horodatées, export et suppression.',
        '<b>En attente :</b> enseignant pour la taxonomie et les définitions de mesure avec les autres axes.',
        '<b>Ensuite :</b> pilote consenti, résultats observés après les prévisions, nouvelle cohorte indépendante.',
        '<b>Frontière :</b> pas de maîtrise cognitive, de transfert piano ni d’efficacité pédagogique inventés.']:
        y=paragraph(text,70,y)-18
    c.showPage();c.save()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ci-url',required=True);p.add_argument('--screenshot',type=Path,nargs='*',default=[])
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report(args.output/'DECLIC_Phase7_Rapport_detaille.pdf',revision,args.ci_url,args.screenshot)
    slides(args.output/'DECLIC_Phase7_Soutenance_5_minutes.pdf',revision)
    print('Detailed report and six-slide defense PDF generated.')
