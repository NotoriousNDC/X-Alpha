from __future__ import annotations
import pandas as pd, numpy as np

def nearest_price(prices, instrument, ts):
    p = prices[prices['instrument']==instrument].copy()
    if p.empty: return None
    p['ts'] = pd.to_datetime(p['ts']); t = pd.to_datetime(ts)
    after = p[p['ts']>=t].sort_values('ts')
    if not after.empty: return float(after.iloc[0]['price'])
    before = p[p['ts']<=t].sort_values('ts')
    if not before.empty: return float(before.iloc[-1]['price'])
    return None

def compute_equity_crypto_outcomes(signals, prices, benchmarks, horizons=('1d','7d','30d')):
    rows = []
    for _, s in signals.iterrows():
        inst, side, post_time = s['instrument'], s['side'], pd.to_datetime(s['posted_at'])
        if not inst: continue
        p0 = nearest_price(prices, inst, s['posted_at'])
        bench = benchmarks.get(inst, None)
        pb0 = nearest_price(prices, bench, s['posted_at']) if bench else None
        if p0 is None: continue
        for h in horizons:
            if not h.endswith('d'): continue
            days = int(h[:-1]); t1 = post_time + pd.Timedelta(days=days)
            p1 = nearest_price(prices, inst, t1.isoformat(sep=' '))
            pb1 = nearest_price(prices, bench, t1.isoformat(sep=' ')) if bench else None
            if p1 is None or (bench and pb1 is None): continue
            ret = (p1 - p0)/p0; ret = -ret if side=='short' else ret
            bench_ret = ((pb1 - pb0)/pb0) if (bench and pb0 and pb1) else 0.0
            rows.append({'signal_id': s['id'], 'evaluation_window': h, 'settled_at': t1.isoformat(sep=' '),
                         'realized_return': ret, 'benchmark_return': bench_ret, 'excess_return': ret-bench_ret,
                         'sharpe_like': None, 'brier': None, 'pnl_per_contract': None, 'clv_points': None,
                         'clv_prob_delta': None, 'won': None, 'notes':'equity/crypto outcome'})
    return pd.DataFrame(rows)

def interpolate_quote(quotes, market_ref, ts):
    q = quotes[quotes['market_ref']==market_ref].copy()
    if q.empty: return None
    q['ts'] = pd.to_datetime(q['ts']); t = pd.to_datetime(ts)
    after = q[q['ts']>=t].sort_values('ts')
    if not after.empty: return float(after.iloc[0]['yes_price'])
    before = q[q['ts']<=t].sort_values('ts')
    if not before.empty: return float(before.iloc[-1]['yes_price'])
    return None

def compute_prediction_outcomes(signals, quotes, resolutions):
    rows = []
    res_map = resolutions.set_index('market_ref').to_dict(orient='index')
    for _, s in signals.iterrows():
        mref, side = s['market_ref'], s['side']
        entry_yes = interpolate_quote(quotes, mref, s['posted_at'])
        if entry_yes is None or mref not in res_map: continue
        outcome = res_map[mref]['outcome']; resolved_at = res_map[mref]['resolved_at']
        entry_price = entry_yes if side=='yes' else (1.0-entry_yes)
        if side=='yes':
            pnl = (1.0 if outcome=='YES' else 0.0) - entry_price; won = 1 if outcome=='YES' else 0
        else:
            pnl = (1.0 if outcome=='NO' else 0.0) - entry_price; won = 1 if outcome=='NO' else 0
        brier = None
        if s.get('odds_price') is not None and not pd.isna(s['odds_price']):
            p = float(s['odds_price']); o = 1.0 if outcome=='YES' else 0.0
            if side=='no': p = 1.0 - p
            brier = (p - o)**2
        rows.append({'signal_id': s['id'],'evaluation_window':'event','settled_at':resolved_at,
                     'realized_return':None,'benchmark_return':None,'excess_return':None,'sharpe_like':None,
                     'brier':brier,'pnl_per_contract':pnl,'clv_points':None,'clv_prob_delta':None,'won':won,'notes':'prediction outcome'})
    return pd.DataFrame(rows)

def team_margin(ev, team):
    return (ev['score1'] or 0) - (ev['score2'] or 0) if team==ev['team1'] else (ev['score2'] or 0) - (ev['score1'] or 0)

def compute_sports_outcomes(signals, events, lines):
    rows = []
    ev_map = events.set_index('event_id').to_dict(orient='index')
    closing = lines[lines['is_closing']==1].copy()
    for _, s in signals.iterrows():
        eid = s['market_ref']
        if eid not in ev_map: continue
        ev = ev_map[eid]; settled_at = ev['start_time']; won=None; clv_points=None; clv_prob_delta=None
        cl = closing[(closing['event_id']==eid) & (closing['line_type']==s['line_type'])]
        if s['line_type']=='spread':
            if not pd.isna(s['line']) and not cl.empty and not pd.isna(cl.iloc[0]['line']):
                clv_points = float(s['line']) - float(cl.iloc[0]['line'])
            if s['team']:
                won = 1 if (team_margin(ev, s['team']) - float(s['line'])) > 0 else 0
        elif s['line_type']=='total':
            posted = float(s['line']) if not pd.isna(s['line']) else None
            total = (ev['score1'] or 0) + (ev['score2'] or 0)
            if not cl.empty and not pd.isna(cl.iloc[0]['line']) and posted is not None:
                closing_total = float(cl.iloc[0]['line'])
                clv_points = (posted - closing_total) if s['side']=='over' else (closing_total - posted)
            if posted is not None:
                won = 1 if (total > posted and s['side']=='over') or (total < posted and s['side']=='under') else 0
        elif s['line_type']=='ml':
            if s['team']: won = 1 if team_margin(ev, s['team']) > 0 else 0
        rows.append({'signal_id': s['id'],'evaluation_window':'event','settled_at':settled_at,
                     'realized_return':None,'benchmark_return':None,'excess_return':None,'sharpe_like':None,
                     'brier':None,'pnl_per_contract':None,'clv_points':clv_points,'clv_prob_delta':clv_prob_delta,'won':won,'notes':'sports outcome'})
    return pd.DataFrame(rows)

def zscore(series):
    s = series.astype(float)
    std = s.std(ddof=0)
    return (s - s.mean()) / (std + 1e-12) if std!=0 else s*0

def build_leaderboard(accounts, signals, outcomes, window_days=90):
    merged = signals[['id','account_id']].merge(outcomes, left_on='id', right_on='signal_id', how='left')
    # Coerce numeric
    for col in ['won','excess_return','brier','clv_points','pnl_per_contract']:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')
    agg = merged.groupby('account_id').agg(
        n_signals=('signal_id','count'),
        win_rate=('won', lambda x: np.nanmean(x)),
        mean_excess_return=('excess_return', lambda x: np.nanmean(x)),
        sharpe_like=('excess_return', lambda x: (np.nanmean(x)/(np.nanstd(x)+1e-9)) if np.isfinite(np.nanstd(x)) else np.nan),
        mean_brier=('brier', lambda x: np.nanmean(x)),
        mean_clv_points=('clv_points', lambda x: np.nanmean(x)),
        mean_pred_pnl=('pnl_per_contract', lambda x: np.nanmean(x)),
    ).reset_index()
    for col in ['win_rate','mean_excess_return','sharpe_like','mean_clv_points','mean_pred_pnl']:
        if col in agg.columns:
            agg[f'{col}_z'] = zscore(agg[col].fillna(agg[col].mean()))
    agg['brier_skill_z'] = zscore(-agg['mean_brier'].fillna(agg['mean_brier'].mean()))
    components = ['win_rate_z','mean_excess_return_z','sharpe_like_z','mean_clv_points_z','mean_pred_pnl_z','brier_skill_z']
    agg['alpha_score'] = agg[components].mean(axis=1)
    today = pd.Timestamp.utcnow().normalize()
    agg['window_days']=window_days
    agg['start_date']=(today-pd.Timedelta(days=window_days)).strftime("%Y-%m-%d")
    agg['end_date']=today.strftime("%Y-%m-%d")
    keep=['account_id','window_days','start_date','end_date','n_signals','win_rate','mean_excess_return','sharpe_like','mean_brier','mean_clv_points','mean_pred_pnl','alpha_score']
    return agg[keep].sort_values('alpha_score', ascending=False).reset_index(drop=True)
