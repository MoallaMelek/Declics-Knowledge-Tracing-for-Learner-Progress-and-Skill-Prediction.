"""Publication figures from actual metrics, without fabricated error intervals."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def plots():
    summary=json.loads((ROOT/'artifacts/phase7/summary.json').read_text(encoding='utf-8'))
    output=ROOT/'artifacts/phase7/figures';output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.labelcolor':'#193d36','text.color':'#193d36','figure.facecolor':'white','savefig.facecolor':'white'})
    conditions=['gru','unordered','recent3','attention','no_concept_embedding','past_gaps']
    names=['GRU complet','Cumuls sans ordre','Trois groupes récents','Attention','Attention sans embeddings','GRU + intervalles passés']
    fig,ax=plt.subplots(figsize=(9.4,4.7))
    for index,seed in enumerate((42,17,83)):
        scores=[next(r['test'] for r in summary['variants'] if r['source']=='singpad' and r['seed']==seed and r['condition']==condition) for condition in conditions]
        ax.scatter(scores,np.arange(6)+(index-1)*.15,s=42,color=['#215c49','#a46e31','#688ca4'][index],label=f'Graine {seed}',zorder=3)
    means=[np.mean([r['test'] for r in summary['variants'] if r['source']=='singpad' and r['condition']==condition]) for condition in conditions]
    ax.scatter(means,np.arange(6),marker='|',s=210,color='#182e26',label='Moyenne descriptive',zorder=4)
    ax.set_yticks(np.arange(6),names);ax.invert_yaxis();ax.set_xlabel('Log-loss test par note - plus faible = mieux')
    ax.set_title('SingPAD : comparaison des représentations',loc='left',fontweight='bold',pad=16)
    ax.grid(axis='x',alpha=.2);ax.legend(loc='lower right',fontsize=8)
    fig.text(.02,.01,'Trois partitions pouvant partager des apprenants ; points réels, sans intervalle de confiance inventé.',fontsize=8,color='#566c65')
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(output/'representations-singpad.png',dpi=180);plt.close(fig)
    calibration=summary['reliability_example'];fig,ax=plt.subplots(figsize=(7.5,4.8))
    ax.plot([0,1],[0,1],'--',color='#8a918b',linewidth=1,label='Correspondance idéale')
    for key,color,label in [('test_raw','#215c49','Brut'),('test_scaled','#a46e31','Température validation')]:
        bins=calibration[key]['calibration']
        ax.plot([b['prediction'] for b in bins],[b['observed'] for b in bins],'-o',color=color,label=label,markersize=5)
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Probabilité moyenne prévue',ylabel='Fraction de notes réellement réussies')
    ax.set_title('Fiabilité SingPAD - GRU graine 42, test',loc='left',fontweight='bold');ax.legend(fontsize=9);ax.grid(alpha=.15)
    fig.text(.02,.01,'Dix tranches fixes ; moyennes pondérées par notes. Température ajustée sur validation seulement.',fontsize=8,color='#566c65')
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(output/'calibration-singpad.png',dpi=180);plt.close(fig)
    stress=summary['stress']['singpad']['conditions'];labels=['Intact','30 % du passé absent','Deux groupes récents absents','Concept ciblé absent du passé']
    vals=[v['metrics']['log_loss'] for v in stress.values()];fig,ax=plt.subplots(figsize=(9,4.3))
    bars=ax.barh(labels,vals,color=['#215c49','#70917a','#a58552','#b86e4d'],height=.6);ax.invert_yaxis()
    ax.set_xlim(.5,.555);ax.set_xlabel('Log-loss test par note - axe limité à [0,50 ; 0,555]')
    for b,v in zip(bars,vals):ax.text(v+.0005,b.get_y()+b.get_height()/2,f'{v:.6f}',va='center',fontsize=9)
    ax.set_title('Quand le passé manque : même GRU, mêmes cibles',loc='left',fontweight='bold',pad=15)
    ax.grid(axis='x',alpha=.15)
    fig.text(.02,.01,'Stress artificiel, graine 42 ; 62 152 cibles concept-groupe et 148 076 notes inchangées.',fontsize=8,color='#566c65')
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(output/'missing-history-singpad.png',dpi=180);plt.close(fig)
    print('Three measured scientific figures generated.')


if __name__=='__main__':plots()
