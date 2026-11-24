#!/usr/bin/env python3
"""Typeset the main manuscript and independent supplement without source edits.

The manuscript remains authoritative. Table captions, table contents, prose,
math, and reference entries are mechanically converted; no paraphrasing.
"""
from pathlib import Path
import re,hashlib,json,sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'MANUSCRIPT_EN.md'
original=SOURCE.read_text(encoding='utf-8')
CHECK='--check' in sys.argv
def emit(path,text):
    if CHECK:assert path.read_text()==text,f'{path} differs from generated LaTeX'
    else:path.write_text(text)


# User-supplied LaTeX is an opaque payload. Sentinels survive every Markdown,
# typography, metric-macro and cross-reference pass and are restored only at emit.
RAW_TEX={}
RAW_META=[]
segment_file=HERE/'direct_replacements/segments.json'
segment_names=json.loads(segment_file.read_text()) if segment_file.exists() else {}
def capture_raw(match):
    raw=match[1].rstrip('\n')
    token='HUEUSERLATEXBLOCK'+str(len(RAW_TEX)).zfill(4)+'END'
    name=next((name for name,value in segment_names.items() if value.strip()==raw.strip()),token)
    RAW_TEX[token]=raw
    RAW_META.append({'token':token,'name':name,'sha256':hashlib.sha256(raw.encode()).hexdigest(),
                     'tables':len(re.findall(r'\\begin\{table\*?\}',raw))})
    return token+'\n'
working=re.sub(r'^```latex\s*\n([\s\S]*?)^```[ \t]*$',capture_raw,original,flags=re.M)
RAW_TABLE_PREFIX=''
RAW_TABLE_SUFFIX=''
def restore_raw(text):
    for token,raw in RAW_TEX.items():
        text=text.replace(token,raw)
    return text


def esc(s):
    trans={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$', '#':r'\#','_':r'\_',
           '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
           '—':'---','–':'--','→':r'\ensuremath{\rightarrow}',
           '±':r'\ensuremath{\pm}','×':r'\ensuremath{\times}',
           'á':r"\'{a}",'é':r"\'{e}",'í':r"\'{i}",'ó':r"\'{o}",'ú':r"\'{u}",
           'ö':r'\"{o}','ä':r'\"{a}','ü':r'\"{u}','ő':r'\H{o}',
           'č':r'\v{c}','š':r'\v{s}','ń':r"\'{n}"}
    return ''.join(trans.get(c,c) for c in s)


def merge_cites(s):
    return re.sub(
        r'\\cite\{([^}]+)\}(?:\s*,\s*\\cite\{([^}]+)\})+',
        lambda m: r'\cite{' + ','.join(re.findall(r'ref\d+', m.group(0))) + '}',
        s,
    )


def esc_quotes_and_prose(s):
    out=[]
    for idx,ch in enumerate(s):
        if ch=='“':out.append('``')
        elif ch=='”':out.append("''")
        elif ch=='‘':out.append('`')
        elif ch=='’':out.append("'")
        elif ch=='"':
            prev=s[idx-1] if idx>0 else ''
            if idx==0 or prev in ' \t\n([{-—–':out.append('``')
            else:out.append("''")
        else:out.append(esc(ch))
    rendered=''.join(out)
    # Convert standalone numeric citations [N] and [A]--[B] into \cite{...}.
    rendered=re.sub(
        r'\[(\d+)\](?:--|–|-)(\[(\d+)\]|(\d+))',
        lambda m: r'\cite{' + ','.join(f'ref{k}' for k in range(int(m[1]), int(m[3] or m[4]) + 1)) + '}',
        rendered,
    )
    rendered=re.sub(r'\[(\d+)\]',r'\\cite{ref\1}',rendered)
    return merge_cites(rendered)


def inline(s):
    # Protect Markdown backslash-escaped asterisks before parsing emphasis.
    s=s.replace(r'\*', 'HUEESCAPEDSTAR')
    # Recognize math, code, URLs, bold and italic; escape only ordinary text.
    pat=re.compile(r'(\$[^$\n]+\$|`[^`\n]+`|https?://[^\s,)]+|\*\*.+?\*\*|(?<!\*)\*[^*\n]+\*(?!\*))')
    pieces=[];idx=0
    for m in pat.finditer(s):
        pieces.append(esc_quotes_and_prose(s[idx:m.start()]));v=m.group()
        if v.startswith('$'):pieces.append(v)
        elif v.startswith('`'):
            code_tex=esc(v[1:-1]).replace(r'\_',r'\_\allowbreak{}').replace('/',r'/\allowbreak{}').replace('.',r'.\allowbreak{}').replace('=',r'=\allowbreak{}')
            while '--' in code_tex:code_tex=code_tex.replace('--','HUEDBLDASH')
            if not v[1:-1].startswith('--'):code_tex=code_tex.replace('-',r'-\allowbreak{}')
            code_tex=code_tex.replace('HUEDBLDASH','-{}-')
            pieces.append(r'\texttt{'+code_tex+'}')
        elif v.startswith(('http://','https://')):pieces.append(r'\url{'+v+'}')
        elif v.startswith('**'):pieces.append(r'\textbf{'+inline(v[2:-2])+'}')
        else:pieces.append(r'\emph{'+inline(v[1:-1])+'}')
        idx=m.end()
    pieces.append(esc_quotes_and_prose(s[idx:]));rendered=''.join(pieces).replace('HUEESCAPEDSTAR','*')
    for letter,label in [('A','app:color-charts'),('B','app:regularization')]:
        rendered=rendered.replace('Appendix '+letter,r'Appendix~\ref{'+label+'}')
    return rendered


def fmt_table(lines,caption):
    appendix_table=state=="appendix"
    single_column=any(s in caption for s in [
        'S3 Compact Matched-Budget',
        'Frozen Regularized-Energy Transfer',
        'All-Pairs versus Within-Family',
    ])
    rows=[]
    for line in lines:
        cols=[x.strip() for x in line.strip()[1:-1].split('|')]
        if all(re.fullmatch(r':?-{3,}:?',c) for c in cols):continue
        rows.append(cols)
    count=len(rows[0]);assert all(len(r)==count for r in rows),(caption,rows)
    # Tables have fixed report columns. Width proportional to source text length,
    # with bounded fractions so every table fits at IEEE standard 8pt (\footnotesize).
    weights=[max(8,max(len(re.sub(r'\$[^$]+\$|`([^`]+)`',lambda m:m.group(1) or 'math',row[i])) for row in rows)) for i in range(count)]
    weights=[min(w,42) for w in weights];total=sum(weights)
    # parbox column widths sum to textwidth less intercolumn padding (3pt per side).
    widths=[f'{w/total:.6f}' for w in weights]
    if 'Comparison of Black-Box LLM Auditing' in caption and count==6:
        widths=['.12','.17','.19','.17','.16','.19']
    if 'Dataset A (56 Models' in caption and count==6:
        widths=['.14','.10','.20','.19','.18','.19']
    if 'S3 Compact Matched-Budget' in caption and count==6:
        widths=['.07','.31','.15','.15','.15','.17']
    if 'Study S5 Head-to-Head' in caption and count==7:
        widths=['.22','.06','.08','.13','.14','.11','.26']
    if 'Frozen Regularized-Energy Transfer' in caption and count==4:
        widths=['.27','.19','.27','.27']
    if 'Gateway Input/Output' in caption:
        widths=['.17','.10','.10','.15','.24','.24']
    if 'All-Pairs versus Within-Family' in caption and count==6:
        widths=['.15','.13','.18','.18','.18','.18']
    spec=''.join('>{\\raggedright\\arraybackslash}p{\\dimexpr '+v+'\\textwidth-6pt\\relax}' for v in widths)
    cap=re.sub(r'^TABLE\s+(?:[IVX]+|\d+):\s*','',caption)
    out=[r'\begin{table*}[t]',r'\centering',r'\caption{'+inline(cap)+'}',r'\label{tab:source-'+str(len(TABLES)+1)+'}',r'\footnotesize',r'\setlength{\tabcolsep}{3pt}',r'\renewcommand{\arraystretch}{1.08}',r'\begin{tabular}{@{}'+spec+'@{}}',r'\toprule']
    for ix,row in enumerate(rows):
        out.append(' & '.join(inline(c).replace(' / ',r' /\allowbreak{} ') for c in row)+r' \\')
        if ix==0:out.append(r'\midrule')
    out += [r'\bottomrule',r'\end{tabular}',r'\end{table*}']
    rendered='\n'.join(out)
    if single_column:
        pos = '[b]' if 'Frozen Regularized-Energy Transfer' in caption else '[t]'
        rendered=rendered.replace(r'\begin{table*}[t]',r'\begin{table}'+pos).replace(r'\end{table*}',r'\end{table}').replace(r'\textwidth',r'\columnwidth')
    if appendix_table:
        rendered=rendered.replace(r'\begin{table*}[t]',r'\par\noindent\begin{minipage}{\columnwidth}\makeatletter\def\@captype{table}\makeatother').replace(r'\end{table*}',r'\end{minipage}\par\vspace{6pt}').replace(r'\textwidth',r'\columnwidth')
    return rendered


def break_display_math(math, number):
    # Insert alignment without changing formula tokens.
    if number > 0:
        if r'D_{\mathrm{JSD}}(P\|Q)=' in math and r'\begin{aligned}' not in math:
            left, right = math.split(r'+\tfrac12\sum_xQ(x)', 1)
            return (r'\begin{aligned}' + left.replace('=', '&=', 1) + r'\\' + '\n'
                    + r'&\quad+\tfrac12\sum_xQ(x)' + right + r'\end{aligned}')
        if r'W_i(\mathbf c)=' in math and r',\qquad P_{\mathrm{soft}}' in math:
            left, right = math.split(r',\qquad P_{\mathrm{soft}}', 1)
            return (r'\begin{aligned}' + left.replace('=', '&=', 1) + r',\\' + '\n'
                    + r'P_{\mathrm{soft}}' + right.replace('=', '&=', 1) + r'\end{aligned}')
        if r'D_{\mathrm{hyb}}=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}}' in math and r'\begin{aligned}' not in math:
            suffix = '.' if math.rstrip().endswith('.') else ''
            return (r'\begin{aligned}D_{\mathrm{hyb}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}\\&\quad+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}}' + suffix + r'\end{aligned}')
        if r'D_{\mathrm{hyb-reg}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\tilde D_{\mathrm{E-reg}}+0.15D_{\mathrm{side}},' in math:
            math = math.replace(
                r'D_{\mathrm{hyb}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}},',
                r'D_{\mathrm{hyb}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}\\&\quad+0.25\bar D_{\mathrm E}+0.15D_{\mathrm{side}},',
            )
            return math.replace(
                r'D_{\mathrm{hyb-reg}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}+0.25\tilde D_{\mathrm{E-reg}}+0.15D_{\mathrm{side}},',
                r'D_{\mathrm{hyb-reg}}&=0.35D_{\mathrm{vox}}+0.25D_{\mathrm{hex}}\\&\quad+0.25\tilde D_{\mathrm{E-reg}}+0.15D_{\mathrm{side}},',
            )
        if r'\widehat{\mathrm{MMD}}_u^2=' in math and r'\begin{aligned}' not in math:
            left, right = math.split(r'-\frac{2\sum_{i,j}k(x_i,y_j)}{nm}', 1)
            return (r'\begin{aligned}' + left.replace('=', '&=', 1) + r'\\' + '\n'
                    + r'&\quad-\frac{2\sum_{i,j}k(x_i,y_j)}{nm}' + right + r'\end{aligned}')
    markers = [
        r" + \frac{1}{2}\sum_{x \in \operatorname{supp}(Q)}",
        r", \qquad \lim", r", \qquad P_{", r" = \frac{\max\!",
        " = (d_{UV'}", r",\qquad D_{W_2}",
    ]
    if r'\begin{aligned}' in math:
        return math
    matches = [mark for mark in markers if math.count(mark) == 1]
    if not matches:
        return math
    mark=matches[0]
    left,right=math.split(mark,1)
    if mark.startswith(','):
        mark=mark.replace(r"\qquad", "", 1)
        return r"\begin{aligned} &"+left+","+r" \\ &"+mark[1:].lstrip()+right+r"\end{aligned}"
    return r"\begin{aligned} &"+left+r" \\ &"+mark.strip()+right+r"\end{aligned}"


def is_numbered_definition(raw_math):
    return any(tok in raw_math for tok in (
        r'\psi(t)=',
        r'W_i(\mathbf c)=',
        r'\bar D_{\mathrm E}=',
        r'D_{\mathrm{hyb}}&=',
        r'D_{\mathrm{hyb}}=',
    ))


lines=working.splitlines();title=lines[0][2:];abstract=lines[2].split('—',1)[1];keywords=lines[4].split('—',1)[1]
TABLES=[];body=[];appendix=[];target=body;refs=[];biography=[];biography_name='[Author Name]';state='body';caption=None;i=8;major=0;sub=0;math_number=0
formal=None;proof_active=False;biography_raw=False
while i<len(lines):
    line=lines[i];i+=1
    if not line.strip() or line.strip()=='---' or line.startswith('<!--'):continue
    # Compact statements end when ordinary explanatory prose resumes; their
    # complete proofs live in the supplement. Legacy explicit proofs still work.
    if formal is not None and not proof_active and not line.startswith(('*','$$')) and not re.match(r'^\d+\. ',line):
        target.append(r'\end{'+formal+'}');formal=None
    if line=='## References':state='refs';continue
    if line=='## Author Biography':state='biography';continue
    if line in RAW_TEX:
        raw=RAW_TEX[line]
        TABLES.extend([line]*len(re.findall(r'\\begin\{table\*?\}',raw)))
        if state=='biography':
            biography.append(line);biography_raw=True
            names=re.findall(r'\\begin\{IEEEbiographynophoto\}\{([^}]+)\}',raw)
            if names:biography_name=', '.join(names)
        else:target.append(line)
        continue
    if state=='biography':
        name=re.fullmatch(r'\*\*(\[[^\]]+\])\*\*',line)
        if name and not biography:biography_name=name[1]
        else:biography.append(inline(line))
        continue
    # Transitional manuscript headings may still mark already-migrated material.
    if state=='refs' and line.startswith('## Supplement '):break
    if line.startswith('## Appendix '):
        state='appendix';target=appendix
        target.append(r'\section{'+inline(re.sub(r'^## Appendix [A-Z]\. ', '', line))+'}')
        letter=re.match(r'^## Appendix ([A-Z])\.',line)[1]
        target.append(r'\label{'+{'A':'app:color-charts','B':'app:regularization'}[letter]+'}')
        continue
    if state=='refs':
        if line.startswith('### '):continue
        m=re.match(r'^\[(\d+)\]\s+(.*)$',line)
        if not m:raise ValueError('Unexpected bibliography line: '+line)
        refs.append((int(m[1]),inline(m[2])));continue
    statement=re.match(r'^\*\*(Theorem|Proposition|Lemma) (\d+) \((.+?)\)\.?\*\*\.?\s*(.*)$',line)
    if statement:
        assert formal is None and not proof_active
        kind,number,heading,remainder=statement.groups();formal=kind.lower()
        FORMAL_COUNTS = globals().setdefault('FORMAL_COUNTS', {})
        FORMAL_COUNTS[formal] = FORMAL_COUNTS.get(formal, 0) + 1
        assert int(number) == FORMAL_COUNTS[formal], f'{kind} number mismatch: {number} != {FORMAL_COUNTS[formal]}'
        label=({'Theorem':'thm:','Proposition':'prop:','Lemma':'lem:'}[kind])+number
        prefix=r'\begin{'+formal+'}['+inline(heading)+r']\label{'+label+r'}\normalfont '
        if not remainder:
            target.append(prefix.rstrip())
            continue
        target.append(prefix+inline(remainder)+'\n')
        continue
    if line.startswith('*Proof sketch.*'):
        assert formal is not None and not proof_active
        target.append(r'\end{'+formal+'}');formal=None
        target.append(inline(line)+'\n')
        continue
    if line.startswith('*Proof*.'):
        assert formal is not None and not proof_active
        target.append(r'\end{'+formal+'}');formal=None;proof_active=True
        target.append(r'\begin{proof}')
        line=line.removeprefix('*Proof*.').lstrip()
    if line.startswith('**Table note:** '):
        end=r'\end{table*}' if target[-1].endswith(r'\end{table*}') else r'\end{table}'
        assert target[-1].endswith(end)
        width=r'\textwidth' if end==r'\end{table*}' else r'\columnwidth'
        note=r'\par\vspace{3pt}\begin{minipage}{'+width+r'}\footnotesize '+inline(line.removeprefix('**Table note:** '))+r'\end{minipage}'
        target[-1]=target[-1].replace(end,note+'\n'+end)
        continue
    if line.startswith('!['):
        fm=re.fullmatch(r'!\[(.*)\]\((.*)\)',line);assert fm,line
        caption_text,rel=fm.groups();num=int(re.search(r'fig(\d)',rel)[1])
        FIG_NUMS = globals().setdefault('FIG_NUMS', [])
        FIG_NUMS.append(num)
        target.append(r'\begin{figure*}[t]'+ '\n'+r'\centering\includegraphics[width=\textwidth]{'+Path(rel).name+'}\n'+r'\caption{'+inline(caption_text)+r'}\label{fig:'+str(num)+'}'+ '\n'+r'\end{figure*}')
        continue
    if line.startswith('## '):
        title_text=re.sub(r'^(?:[IVX]+|\d+)\.\s*','',line[3:]);target.append(r'\section{'+inline(title_text)+'}');continue
    if line.startswith('### '):
        title_text=re.sub(r'^(?:[A-Z]\.|\d+\.\d+\.?)\s*','',line[4:])
        if '$' in title_text:
            plain_title=esc_quotes_and_prose(title_text.replace('$',''))
            target.append(r'\subsection['+plain_title+r']{\boldmath '+inline(title_text)+'}')
        else:
            target.append(r'\subsection{'+inline(title_text)+'}')
        continue
    if re.match(r'^\*\*TABLE\s+(?:[IVX]+|\d+):',line):
        assert caption is None
        caption=line[2:-2];continue
    if line.startswith('|'):
        tab=[line]
        while i<len(lines) and lines[i].startswith('|'):tab.append(lines[i]);i+=1
        assert caption
        TABLES.append(fmt_table(tab,caption));target.append(TABLES[-1]);caption=None;continue
    if line.startswith('$$'):
        if line.endswith('$$') and len(line)>4: math=line[2:-2]
        else:
            m=[line[2:]]
            while i<len(lines) and not lines[i].endswith('$$'):m.append(lines[i]);i+=1
            assert i<len(lines);m.append(lines[i][:-2]);i+=1;math='\n'.join(m)
        math_number+=1
        env='equation' if is_numbered_definition(math) else 'equation*'
        math=break_display_math(math,math_number)
        target.append(f'\\begin{{{env}}}\n{math}\n\\end{{{env}}}');continue
    # Preserve source list numbering and order without automatic numbering changes.
    m=re.match(r'^(?:- |(\d+)\. )(.*)$',line)
    if m:
        prefix=(m[1]+'. ' if m[1] else r'\textbullet\ ')
        target.append(r'\noindent '+prefix+inline(m[2])+r'\par');continue
    proof_end=line.endswith(r'$\blacksquare$')
    if proof_end:
        assert proof_active
        line=line.removesuffix(r'$\blacksquare$').rstrip()
    prev_eq=bool(target) and (target[-1].endswith(r'\end{equation}') or target[-1].endswith(r'\end{equation*}'))
    cont_after_eq=prev_eq and bool(re.match(r'^\*?[a-z]',line))
    target.append((r'\noindent ' if cont_after_eq else '')+inline(line)+'\n')
    if proof_end:
        target.append(r'\end{proof}');proof_active=False
assert len(TABLES)>0 and refs and [n for n,_ in refs]==list(range(1,len(refs)+1))
assert globals().get('FIG_NUMS') == list(range(1, len(globals().get('FIG_NUMS', [])) + 1)), f"Figures out of sequential order: {globals().get('FIG_NUMS')}"
assert caption is None and formal is None and not proof_active
bibliography='\\begin{thebibliography}{99}\n'+'\n'.join('\\bibitem{ref'+str(n)+'} '+text for n,text in refs)+'\n\\end{thebibliography}\n'
main_prose=original.split('## References',1)[0]
citation_prose=re.sub(r'\$\$[\s\S]*?\$\$|\$[^$]*\$','',main_prose)
citation_prose=re.sub(r'\[(\d+)\]\s*[–-]\s*\[(\d+)\]',r'[\1-\2]',citation_prose)
cited=set()
for group in re.findall(r'\[(\d+(?:\s*[,–-]\s*\d+)*)\]',citation_prose):
    for part in group.split(','):
        bounds=re.split(r'[–-]',part.strip())
        cited.update(range(int(bounds[0]),int(bounds[-1])+1))
for cnum in re.findall(r'\\cite\{([^}]+)\}',citation_prose):
    for key in cnum.split(','):
        m_key=re.fullmatch(r'ref(\d+)',key.strip())
        if m_key:cited.add(int(m_key[1]))
main_reference_numbers=sorted(cited)
assert set(main_reference_numbers) <= {n for n,_ in refs}
main_refs=[(n,text) for n,text in refs if n in main_reference_numbers]
if main_reference_numbers==list(range(1,len(main_refs)+1)):
    main_bibliography='\\begin{thebibliography}{99}\n'+'\n'.join('\\bibitem{ref'+str(n)+'} '+text for n,text in main_refs)+'\n\\end{thebibliography}\n'
else:
    main_bibliography='\\begin{thebibliography}{99}\n'+'\n'.join('\\bibitem['+str(n)+']{ref'+str(n)+'} '+text for n,text in main_refs)+'\n\\end{thebibliography}\n'
common=r'''\ifdefined\XeTeXversion\else
\usepackage[utf8]{inputenc}
\fi
\usepackage{amsmath,amssymb,amsfonts,graphicx,array,tabularx,booktabs,textcomp,cite}
\graphicspath{{../../figs/}{./}}
% Breakable statement headings for both two-column classes.
\newcounter{theorem}
\newenvironment{theorem}[1][]{\refstepcounter{theorem}\par\smallskip\noindent\textbf{Theorem \thetheorem\ (#1).}\ }{\par\smallskip}
\newcounter{proposition}
\newenvironment{proposition}[1][]{\refstepcounter{proposition}\par\smallskip\noindent\textbf{Proposition \theproposition\ (#1).}\ }{\par\smallskip}
\newcounter{lemma}
\newenvironment{lemma}[1][]{\refstepcounter{lemma}\par\smallskip\noindent\textbf{Lemma \thelemma\ (#1).}\ }{\par\smallskip}
\newenvironment{proof}{\par\noindent\textit{Proof.}\ }{\unskip\nobreak\hfill$\blacksquare$\par}
\usepackage{url}
\emergencystretch=2em
\setlength{\parskip}{0ex plus 2.2ex minus 0.12ex}
\DeclareFontShape{OMS}{cmsy}{m}{n}{<-7>cmsy5<7-9>cmsy7<9->cmsy10}{}
\DeclareFontShape{OML}{cmm}{m}{it}{<-7>cmmi5<7-9>cmmi7<9->cmmi10}{}
'''

metric_macros = {
 r'D_{\mathrm{hex}}':r'\Dhex', r'D_{\mathrm{vox}}':r'\Dvox',
 r'\bar D_{\mathrm E}':r'\Denergy',
 r'\tilde D_{\mathrm{E-reg}}':r'\Dereg', r'D_{W_2}':r'\DWtwo',
 r'D_{\mathrm{side}}':r'\Dside', r'D_{\mathrm{hyb}}':r'\Dhyb',
 r'D_{\mathrm{hyb-reg}}':r'\Dhybreg',
 r'\tilde{D}_{\text{energy-reg}}':r'\Dereg',r'D_{\mathrm{energy-reg}}':r'\Dereg',
 r'\tilde{D}_{E\text{-reg}}':r'\Dereg',r'\tilde{D}_{\text{energy}}':r'\Denergy',
 r'\tilde{D}_{W_2}':r'\DWtwo',r'D_{\mathrm{hyb\text{-}reg}}':r'\Dhybreg',
 r'D_{\text{hybrid-reg}}':r'\Dhybreg',r'D_{\text{hex}}':r'\Dhex',
 r'D_{\text{voxel}}':r'\Dvox',
 r'D_{\text{hybrid}}':r'\Dhyb',r'D_{\text{side}}':r'\Dside'
}
macro_expansions = [
 (r'\Dhex', r'D_{\mathrm{hex}}'),
 (r'\Dvox', r'D_{\mathrm{vox}}'),
 (r'\Denergy', r'\bar D_{\mathrm E}'),
 (r'\Dereg', r'\tilde D_{\mathrm{E\mbox{-}reg}}'),
 (r'\DWtwo', r'D_{W_2}'),
 (r'\Dside', r'D_{\mathrm{side}}'),
 (r'\Dhyb', r'D_{\mathrm{hyb}}'),
 (r'\Dhybreg', r'D_{\mathrm{hyb\mbox{-}reg}}'),
]
macro_defs='\n'.join(r'\newcommand{'+v+'}{'+k+'}' for v,k in macro_expansions)+'\n'
def standardize(t):
    for k,v in sorted(metric_macros.items(),key=lambda kv:-len(kv[0])):t=t.replace(k,v+'{}')
    return t


def typeset_paragraphs(text):
    """Permit legitimate line breaks without changing manuscript wording."""
    for old,new in [
        ('chat-completion',r'chat-\hspace{0pt}completion'),
        ('odd/even',r'odd/\allowbreak{}even'),
        ('Exact-category',r'Exact-\hspace{0pt}category'),
        (r"Coronado-Bl\'{a}zquez",r"Coronado-\hspace{0pt}Bl\'{a}zquez"),
    ]:
        text=text.replace(old,new)
    prefixes=(r'\textbf{Verifier Capabilities.}',
              r'\textbf{Equality versus behavioral tolerance.}',
              'We use three development protocols:')
    paragraphs=text.split('\n\n')
    for i,p in enumerate(paragraphs):
        if p.lstrip().startswith(prefixes):
            if p.lstrip().startswith(r'\textbf{Equality versus behavioral tolerance.}'):
                p=r'\noindent '+p
            paragraphs[i]=r'{\hyphenpenalty=50 '+p+r'\par}'
        elif p.lstrip().startswith(r'\noindent 1. \textbf{Discrete information.}'):
            paragraphs[i]=r'{\rightskip=0pt plus 1em '+p+r'\par}'
    text='\n\n'.join(paragraphs)
    text=re.sub(r'(\\bibitem(?:\[\d+\])?\{ref15\}) ([^\n]+)',r'\1 {\\hyphenpenalty=50 \\rightskip=0pt plus 1em \2\\par}',text)
    return re.sub(r'[ \t]+\n', '\n', text)


def compsoc_crossrefs(text):
    """Render prose references in the numbering used by Computer Society."""
    def roman(value):
        nums={'I':1,'V':5,'X':10}
        return sum(-nums[c] if i+1<len(value) and nums[c]<nums[value[i+1]] else nums[c]
                   for i,c in enumerate(value))
    def replace(match):
        kind,sep,major,minor=match.groups()
        return kind+sep+str(roman(major))+('.'+str(ord(minor)-64) if minor else '')
    return re.sub(r'\b(Sections?|Tables?)([ ~])([IVX]+)(?:-([A-Z]))?\b',replace,text)

body=[standardize(t) for t in body]
appendix=[standardize(t) for t in appendix]
common += macro_defs

from build_supplement import render_supplement
supp_ref_nums=render_supplement(HERE, inline, esc, break_display_math, refs, typeset_paragraphs, standardize, macro_defs, CHECK, compsoc_crossrefs)

project=HERE/'ieee'
if not CHECK:
    project.mkdir(parents=True, exist_ok=True)
cls=(r'\renewcommand{\rmdefault}{ppl}'+'\n'+r'\RequirePackage[T1]{fontenc}'+'\n'+r'\documentclass[10pt,journal,compsoc]{IEEEtran}'+'\n'+
     r'\IfFileExists{pplrc8t.tfm}{}{\renewcommand{\IEEEPARstartWORDFONTSTYLE}{\fontsize{7.5pt}{11.4pt}\selectfont}\renewcommand{\IEEEPARstartWORDCAPSTYLE}{\MakeUppercase}}')
author = r'\author{[Author Name]\IEEEcompsocitemizethanks{\IEEEcompsocthanksitem {[Author Name]} is with [Department, University] (e-mail: [email@edu.cn]).}}'
author_source=HERE/'direct_replacements/author.tex'
if author_source.exists():
    author=author_source.read_text().rstrip('\n')
author_meta_path=HERE/'direct_replacements/author_metadata.json'
pdf_author=json.loads(author_meta_path.read_text())['name'] if author_meta_path.exists() else '[Author Name]'
pdf_title=title.replace('\\',r'\\').replace('(',r'\(').replace(')',r'\)')
pdf_author_esc=pdf_author.replace('\\',r'\\').replace('(',r'\(').replace(')',r'\)')
docinfo=(r'\ifdefined\XeTeXversion\special{pdf:docinfo << /Title ('+pdf_title+r') /Author ('+pdf_author_esc+r') >>}\else\pdfinfo{/Title ('+pdf_title+r') /Author ('+pdf_author_esc+r')}\fi'+'\n')
titlepart=('\\title{'+inline(title)+'}\n'+author+'\n\\begin{document}\n'+docinfo+
           '\\IEEEtitleabstractindextext{\n\\begin{abstract}\n'+inline(abstract)+
           '\n\\end{abstract}\n\\begin{IEEEkeywords}\n'+inline(keywords)+
           '\n\\end{IEEEkeywords}\n}\n\\maketitle\n\\IEEEdisplaynontitleabstractindextext\n')
tex=cls+'\n'+common+standardize(titlepart)+'\n\\input{body}\n\\input{references}\n\\input{biography}\n\\end{document}\n'
emit(project/'main.tex',merge_cites(restore_raw(tex)))
body_text=typeset_paragraphs('\n\n'.join(body)+'\n')
body_text=body_text.replace(r'Appendix~\ref{app:color-charts}',r'Supplement~A').replace(r'Appendix~\ref{app:regularization}',r'Supplement~B')
body_text=compsoc_crossrefs(body_text)
heading='Within-Pool Self-Verification vs. Cross-Template Shift (Dataset C)'
body_text=body_text.replace(r'\subsection{'+heading+'}',r'\subsection['+heading+r']{\raggedright '+heading+'}')
emit(project/'body.tex',merge_cites(restore_raw(body_text)))
emit(project/'references.tex',typeset_paragraphs(main_bibliography))
if biography:
    biography_text='\n\n'.join(biography)+'\n'
    if biography_raw:
        biography_text=restore_raw(biography_text)
    else:
        biography_text=r'\begin{IEEEbiographynophoto}{'+inline(biography_name)+'}\n'+biography_text+r'\end{IEEEbiographynophoto}'+'\n'
else:biography_text='% No author biography supplied in the source manuscript.\n'
emit(project/'biography.tex',biography_text)
emit(project/'source_manifest.json',json.dumps({'source':'../MANUSCRIPT_EN.md','sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'tables':len(TABLES),'references':len(main_refs),'main_reference_numbers':main_reference_numbers,'shared_reference_pool':len(refs),'supplement_references':len(supp_ref_nums),'supplement_reference_numbers':supp_ref_nums,'author_biography_present':bool(biography),'author_biography_name':biography_name,'raw_latex_blocks':RAW_META,'source_language':'English','figure_files':'../../figs/','format':'IEEE Computer Society journal','supplement':'../supplement/main.pdf'},indent=2)+'\n')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==hashlib.sha256(original.encode()).hexdigest()
if RAW_META:
    emit(HERE/'direct_replacements/layout_replacements.json',json.dumps({
        'records':[],
        'wrappers':[],
        'literal_modifications':False,
    },indent=2)+'\n')
print('Verified' if CHECK else 'Generated', f'main manuscript and supplement: {len(TABLES)} main tables, {len(main_refs)} main references, {len(supp_ref_nums)} supplement references ({len(refs)} pool).')
