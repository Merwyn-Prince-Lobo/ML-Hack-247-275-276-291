import json
from pathlib import Path
import joblib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import folium
from .experiments import ROOT, RESULTS, dataset
from .core import probabilities, decode, route_geometry

FIGURES = RESULTS/'figures'

def main():
    FIGURES.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 140})
    models = json.loads((RESULTS/'models.json').read_text())
    final = json.loads((RESULTS/'final.json').read_text())
    names = list(models)
    short = ['Logistic','Gaussian NB','Tree','Forest','Gradient boost']
    fig, axes = plt.subplots(1,3,figsize=(12,3.5))
    axes[0].bar(short,[models[n]['cv_macro_f1'] for n in names], color='#267eaa')
    axes[0].set_title('Trip-grouped CV Macro F1')
    x=np.arange(len(names));w=.38
    axes[1].bar(x-w/2,[models[n]['student_test']['aggregate']['top1_accuracy'] for n in names],w,label='Top-1',color='#267eaa')
    axes[1].bar(x+w/2,[models[n]['student_test']['aggregate']['macro_f1'] for n in names],w,label='Macro F1',color='#25a783')
    axes[1].set_xticks(x,short);axes[1].set_title('Student-test point metrics');axes[1].legend(fontsize=8)
    axes[2].bar(short,[models[n]['student_test']['aggregate']['log_loss'] for n in names],color='#d5963e');axes[2].set_title('Student-test candidate log loss')
    for ax in axes: ax.tick_params(axis='x',rotation=30);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.tight_layout();fig.savefig(FIGURES/'model_comparison.png');plt.close(fig)
    fig, axes=plt.subplots(1,5,figsize=(13,2.8))
    for ax,name,label in zip(axes,names,short):
        a=np.array(models[name]['student_test']['candidate_confusion_matrix']);ax.imshow(np.log1p(a),cmap='Blues')
        for i in range(2):
            for j in range(2): ax.text(j,i,str(a[i,j]),ha='center',va='center',fontsize=8,color='black')
        ax.set_title(label);ax.set_xticks([0,1],['Other','True arc']);ax.set_yticks([0,1],['Other','True arc']);ax.set_xlabel('Selected candidate')
    fig.suptitle('Candidate confusion counts (diagnostic, not arc-class matrices)');fig.tight_layout();fig.savefig(FIGURES/'confusion.png');plt.close(fig)
    import pandas as pd
    trials=pd.read_csv(RESULTS/'bayesian_trials.csv')
    fig,ax=plt.subplots(figsize=(8,3));ax.plot(trials['number'],trials['value'],'o-',label='Trial CV score');ax.plot(trials['number'],trials['value'].cummax(),label='Best so far');ax.set(xlabel='TPE trial',ylabel='Grouped CV Macro F1',title='Actual Bayesian optimisation history');ax.legend();fig.tight_layout();fig.savefig(FIGURES/'search.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,3))
    raw=final['classifier_only']['per_trip'];hmm=final['hmm']['per_trip'];x=np.arange(len(raw))
    for ax,key,title in zip(axes,['macro_f1','route_continuity'],['Per-trip Macro F1','Directed route continuity']):
        ax.plot(x,[r[key] for r in raw],'o-',label='Classifier');ax.plot(x,[r[key] for r in hmm],'o-',label='HMM');ax.set_xticks(x,[r['trip_id'][-2:] for r in raw]);ax.set_title(title);ax.set_xlabel('Student-test trip suffix');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(FIGURES/'decoder.png');plt.close(fig)
    # Representative trip chosen by fixed ordering, never a hand-corrected route.
    record=dataset('student_test')[0];trip=record['trip'];c=record['c']
    model=joblib.load(ROOT/'artifacts'/'model.joblib');p=probabilities(model,c['x']);pred,_,_=decode(trip,c,p,beta=final['decoder_beta'])
    _,lines,_=route_geometry(trip,pred)
    fig,ax=plt.subplots(figsize=(9,5))
    ax.add_collection(LineCollection(trip.nodes[trip.arcs],colors='#c2c9d0',linewidths=.45,label='Road network'))
    ax.add_collection(LineCollection(trip.nodes[trip.arcs[record['route']]],colors='#b74caa',linewidths=4,alpha=.6,label='Reference route'))
    ax.add_collection(LineCollection(lines,colors='#159a76',linewidths=1.8,label='Predicted route'))
    ax.scatter(trip.gps[:,0],trip.gps[:,1],s=3,c='#277fca',label='GPS')
    margin=np.ptp(trip.gps[:,:2],axis=0)*.08
    ax.set_xlim(trip.gps[:,0].min()-margin[0],trip.gps[:,0].max()+margin[0]);ax.set_ylim(trip.gps[:,1].min()-margin[1],trip.gps[:,1].max()+margin[1]);ax.set_aspect(1/np.cos(np.deg2rad(trip.gps[:,1].mean())));ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',title=f'Student-test trip {trip.trip_id}: observed, reference and predicted');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIGURES/'geography.png');plt.close(fig)
    maps=RESULTS/'maps';maps.mkdir(exist_ok=True)
    m=folium.Map(location=trip.gps[:,:2].mean(axis=0)[::-1],zoom_start=13,tiles='OpenStreetMap')
    for name,segments,color,weight in [('Road network',trip.nodes[trip.arcs],'#718096',1),('Reference route (development only)',trip.nodes[trip.arcs[record['route']]],'#bd3dac',6),('Predicted route',lines,'#13a681',3)]:
        layer=folium.FeatureGroup(name=name,show=True)
        for segment in segments: folium.PolyLine(np.asarray(segment)[:,::-1].tolist(),color=color,weight=weight,opacity=.7).add_to(layer)
        layer.add_to(m)
    layer=folium.FeatureGroup(name='Raw GPS')
    for point in trip.gps: folium.CircleMarker(point[:2][::-1].tolist(),radius=2,color='#247dce',fill=True,fill_opacity=.8,tooltip=f't={point[2]:.0f}s').add_to(layer)
    layer.add_to(m);folium.LayerControl().add_to(m);m.fit_bounds([trip.gps[:,:2].min(axis=0)[::-1].tolist(),trip.gps[:,:2].max(axis=0)[::-1].tolist()])
    m.get_root().html.add_child(folium.Element('<div style="position:fixed;bottom:25px;left:20px;background:white;padding:12px;z-index:9999;font:13px sans-serif">PathSnap / student-test 00000000<br><span style="color:#247dce">Blue: GPS</span> | <span style="color:#bd3dac">Purple: reference</span> | <span style="color:#13a681">Green: prediction</span></div>'))
    m.save(str(maps/'student_test_00000000.html'))
    print('Saved actual plots and Folium map',flush=True)
