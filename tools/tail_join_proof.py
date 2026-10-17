#!/usr/bin/env python3
"""Clipped source-vector enlargements before/after the attachment refinement."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from alphabet_sheet import plt,load_glif,PathPatch,BG,INK


def main():
    records=json.loads(Path('data/smooth-tail-joins/manifest.json').read_text())
    transforms={(r['character'],r['role']):r['transform'] for r in json.loads(Path('data/exact-author-tails/manifest.json').read_text())}
    fig,axes=plt.subplots(5,4,figsize=(18,20),facecolor=BG)
    for k,r in enumerate(records):
        s,_,_,_,dx,dy=transforms[r['character'],r['role']];mid=577*s+dx
        for j,(field,label) in enumerate([('previous','Было'),('path','Исправлено')]):
            ax=axes[k//2,(k%2)*2+j];ax.set_facecolor(BG)
            ax.add_patch(PathPatch(load_glif(r[field]).path,facecolor=INK,edgecolor='none'))
            ax.set_xlim(mid-145,mid+130);ax.set_ylim(-140,200);ax.set_aspect('equal')
            ax.axhline(0,color='#c6ad9e',lw=.6);ax.axhline(-30,color='#7faaa4',lw=.6,ls='--')
            ax.set_title(f"{r['character']} · {r['role']} · {label}",fontsize=13)
            ax.set_xticks([]);ax.set_yticks([])
            for spine in ax.spines.values():spine.set_visible(False)
    fig.suptitle('Стыки хвостиков · 1.010 / 1.011\nКапля ниже пунктирной линии сохранена точно',fontsize=21)
    fig.subplots_adjust(top=.91,wspace=.12,hspace=.16,left=.02,right=.98,bottom=.015)
    Path('build/tail-joins').mkdir(parents=True,exist_ok=True)
    fig.savefig('docs/img/tail_join_refinement.svg',facecolor=BG)
    fig.savefig('build/tail-joins/comparison.png',dpi=100,facecolor=BG)
    plt.close(fig)
if __name__=='__main__':main()
