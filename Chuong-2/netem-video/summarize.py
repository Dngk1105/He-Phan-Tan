import json,sys
for l in open(sys.argv[1]):
    r=json.loads(l); e=r['errors']
    print(f"{r['label']:22s} ping={r['ping']['avg']} lost%={r['iperf'].get('lost_pct')} jit={r['iperf'].get('jitter_ms')} fr={r['frames']} 1st={r['first_frame_s']} stall={r['stall_s']}/{r['longest_stall_s']}/{r['n_stalls']} err[corr,inv,conc,ts,cont,dec]={e['corrupt']},{e['invalid']},{e['conceal']},{e['ts_err']},{e['continuity']},{e['decode_err']}")
