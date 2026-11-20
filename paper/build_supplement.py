"""Render the editable English supplement with Unicode prompt originals."""
from pathlib import Path
import hashlib
import json
import re


def render_supplement(here, inline, esc, break_math, refs, typeset_paragraphs, standardize=lambda x:x, macro_defs='', check=False, crossrefs=lambda x:x):
    source = here/'SUPPLEMENT_EN.md'
    original = source.read_text()
    project = here/'supplement'
    if not check:
        project.mkdir(parents=True, exist_ok=True)

    def emit(name, text):
        path = project/name
        if check:
            assert path.read_text() == text, f'Out-of-date supplement: {name}'
        else:
            path.write_text(text)

    def text(value):
        # Unicode prompt originals retain language-specific shaping and direction.
        lang = re.match(r'^\*\*(en|zh|ru|ar):\*\*\s*(.*)$', value)
        if lang:
            code, prompt = lang.groups()
            # Keep CSS double hyphens and original punctuation literally; TeX's
            # typographic --/--- ligatures would silently change probe strings.
            rendered = ''.join(c if c in '—–' else esc(c) for c in prompt)
            if code == 'zh':
                rendered = r'{\cjkfont\addfontfeatures{Ligatures=TeXOff}\XeTeXlinebreaklocale "zh"\XeTeXlinebreakskip=0pt plus 1pt '+rendered+'}'
            elif code == 'ru':
                rendered = r'{\cyrillicfont\addfontfeatures{Ligatures=TeXOff} '+rendered+'}'
            elif code == 'ar':
                ar_ltr = re.compile(r'(\([0-9A-Za-z,#-]+\)|#[0-9A-Za-z]+|[0-9A-Za-z]+(?:[,-][0-9A-Za-z]+)*)')
                parts = []
                for idx_p, seg in enumerate(ar_ltr.split(prompt)):
                    if not seg:
                        continue
                    esc_seg = ''.join(c if c in '—–' else esc(c) for c in seg)
                    if idx_p % 2 == 1:
                        parts.append(r'\textenglish{\addfontfeatures{Ligatures=TeXOff}'+esc_seg+'}')
                    else:
                        parts.append(esc_seg)
                rendered = r'\textarabic{\addfontfeatures{Ligatures=TeXOff} '+''.join(parts)+'}'
            else:
                rendered = r'{\addfontfeatures{Ligatures=TeXOff} '+rendered+'}'
            return r'{\raggedright\noindent\textbf{'+code+r':}\quad '+rendered+r'\par}'
        value = standardize(inline(value))
        # Make long endpoint identifiers breakable without changing characters.
        value = re.sub(r'\\texttt\{([^{}]*)\}', lambda m: r'\texttt{'+re.sub(r'/(?!$)',r'/\\allowbreak{}',m[1]).replace('-',r'-\allowbreak{}')+'}', value)
        return value

    lines = original.splitlines()
    raw_supp_title = lines[0].removeprefix('# ').strip()
    out = []
    caption = None
    table_count = 0
    section_headings = []
    i = 1
    formal = proof = False
    while i < len(lines):
        line = lines[i]; i += 1
        if not line.strip() or line == '---' or line.startswith('<!--'):
            continue
        if line.startswith('## '):
            heading = line[3:]
            label = None
            if heading.startswith(('Appendix A.', 'A.')):
                heading = 'A. '+heading.split('.', 1)[1].strip();label='app:color-charts'
            if heading.startswith(('Appendix B.', 'B.')):
                heading = 'B. '+heading.split('.', 1)[1].strip();label='app:regularization'
            section_headings.append(heading)
            out.append(r'\Needspace{10\baselineskip}\section*{'+text(heading)+'}'+r'\addcontentsline{toc}{section}{'+text(heading)+'}'+(r'\label{'+label+'}' if label else ''))
            continue
        if line.startswith('### '):
            out.append(r'\subsection*{'+text(line[4:])+'}');continue
        if re.match(r'^\*\*TABLE\s+',line):
            caption=line[2:-2];continue
        if line.startswith('|'):
            rows=[]
            while True:
                row=[x.strip() for x in line.strip()[1:-1].split('|')]
                if not all(re.fullmatch(r':?-{3,}:?',x) for x in row):rows.append(row)
                if i>=len(lines) or not lines[i].startswith('|'):break
                line=lines[i];i+=1
            count=len(rows[0]);assert all(len(r)==count for r in rows)
            table_count+=1
            if caption and 'Endpoint Labels' in caption:
                widths=[.31,.27,.10,.32]
            elif caption and 'Complete Study S3 Matched-Budget' in caption and count==9:
                widths=[.05,.23,.10,.10,.10,.10,.10,.10,.12]
            elif caption and 'Complete Study S1' in caption and count==7:
                widths=[.20,.10,.09,.10,.11,.20,.20]
            elif caption and 'Additional Study S1' in caption and count==7:
                widths=[.20,.15,.08,.09,.10,.19,.19]
            elif caption and 'Private Prompt-Pool Subsampling' in caption and count==5:
                widths=[.24,.23,.16,.16,.21]
            elif caption and 'Study S5 Mixed-Routing' in caption and count==7:
                widths=[.07,.24,.08,.14,.17,.14,.16]
            elif caption and 'Study S5 Nine-Day' in caption and count==6:
                widths=[.26,.16,.11,.13,.17,.17]
            elif caption and 'Matched V/U Comparison' in caption and count==5:
                widths=[.28,.18,.18,.18,.18]
            elif caption and 'Median Per-Endpoint Query Overhead' in caption and count==6:
                widths=[.15,.09,.25,.23,.14,.14]
            else:
                widths=[1/count]*count
            spec=''.join(r'>{\raggedright\arraybackslash}p{\dimexpr '+str(w)+r'\linewidth-2\tabcolsep\relax}' for w in widths)
            inventory = bool(caption and 'Endpoint Labels' in caption)
            if inventory:
                tab=[r'{\small\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.12}',r'\begin{NoHyper}\begin{longtable}{@{}'+spec+'@{}}',r'\multicolumn{'+str(count)+r'}{c}{\textbf{'+text(caption or '')+r'}}\\[4pt]',r'\toprule']
            else:
                tab=[r'\par\medskip\noindent\begin{minipage}{\linewidth}\small\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.12}',r'\centering\textbf{'+text(caption or '')+r'}\par\smallskip',r'\begin{tabular}{@{}'+spec+'@{}}',r'\toprule']
            header=' & '.join(text(c) for c in rows[0])+r' \\ \midrule'
            if inventory:tab.extend([header,r'\endfirsthead',r'\toprule',header,r'\endhead',r'\bottomrule\endfoot'])
            else:tab.append(header)
            tab.extend(' & '.join(text(c) for c in row)+r' \\' for row in rows[1:])
            tab += ([r'\end{longtable}\end{NoHyper}',r'}'] if inventory else [r'\bottomrule\end{tabular}',r'\end{minipage}\par\medskip'])
            out.append('\n'.join(tab));caption=None;continue
        named_proof=re.match(r'^\*((?:Proof of [^*]+|Corollary[^*]+))\.\*\s*(.*)$',line)
        if named_proof:
            assert not formal and not proof
            proof_heading,line=named_proof.groups()
            proof=True
            out.append(r'\begin{proof}['+text(proof_heading)+']')
        statement=re.match(r'^\*\*(Proposition|Theorem|Lemma) (\d+) \((.+)\)\*\*\.\s*(.*)$',line)
        if statement:
            kind,number,heading,line=statement.groups()
            formal=kind.lower()
            out.append(r'\begin{'+formal+'}['+text(heading)+']')
        if line.startswith('*Proof*.'):
            assert formal
            out.append(r'\end{'+formal+r'}\begin{proof}');formal=False;proof=True
            line=line.removeprefix('*Proof*.').lstrip()
        if line.startswith('$$'):
            if line.endswith('$$') and len(line)>4:
                formula=line[2:-2]
            else:
                parts=[line[2:]]
                while i<len(lines) and not lines[i].endswith('$$'):parts.append(lines[i]);i+=1
                parts.append(lines[i][:-2]);i+=1;formula='\n'.join(parts)
            out.append('\\[\n'+standardize(break_math(formula,0))+'\n\\]');continue
        ends=line.endswith(r'$\blacksquare$')
        if ends:line=line.removesuffix(r'$\blacksquare$').rstrip()
        if re.match(r'^\d+\. ',line):
            out.append(r'\noindent '+text(line)+r'\par')
        elif re.match(r'^\*\*\w+\*\* \(',line):
            out.append(r'\Needspace{8\baselineskip}'+text(line)+'\n')
        else:
            out.append(text(line)+'\n')
        if ends:
            assert proof
            out[-1]=out[-1].rstrip()+r'\end{proof}'
            proof=False
    assert not formal and not proof
    preamble=r'''\documentclass[10pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{fontspec}
\usepackage{amsmath,amssymb,amsthm,array,longtable,booktabs,url,needspace,cite}
\renewcommand{\citepunct}{], [}
\renewcommand{\citedash}{]--[}
\usepackage[hidelinks,hypertexnames=false]{hyperref}
\hypersetup{pdftitle={'''+raw_supp_title+r'''},pdfauthor={[Author Name]}}
\usepackage{polyglossia}
\setdefaultlanguage{english}
\setotherlanguage{arabic}
\setmainfont[BoldFont=lmroman10-bold.otf,ItalicFont=lmroman10-italic.otf,BoldItalicFont=lmroman10-bolditalic.otf]{lmroman10-regular.otf}
\IfFileExists{/System/Library/Fonts/STHeiti Medium.ttc}{%
  \newfontfamily\cjkfont[Path=/System/Library/Fonts/]{STHeiti Medium.ttc}%
}{%
  \IfFontExistsTF{Noto Sans CJK SC}{\newfontfamily\cjkfont{Noto Sans CJK SC}}{%
    \IfFontExistsTF{WenQuanYi Zen Hei}{\newfontfamily\cjkfont{WenQuanYi Zen Hei}}{%
      \newfontfamily\cjkfont{FandolHei-Regular.otf}%
    }%
  }%
}
\IfFileExists{../fonts/DejaVuSans.ttf}{%
  \newfontfamily\cyrillicfont[Path=../fonts/]{DejaVuSans.ttf}%
}{%
  \IfFileExists{DejaVuSans.ttf}{\newfontfamily\cyrillicfont[Path=./]{DejaVuSans.ttf}}{\newfontfamily\cyrillicfont{DejaVu Sans}}%
}
\IfFileExists{/System/Library/Fonts/Supplemental/Arial.ttf}{%
  \newfontfamily\arabicfont[Path=/System/Library/Fonts/Supplemental/,Script=Arabic]{Arial.ttf}%
}{%
  \IfFontExistsTF{Noto Naskh Arabic}{\newfontfamily\arabicfont[Script=Arabic]{Noto Naskh Arabic}}{%
    \IfFileExists{../fonts/DejaVuSans.ttf}{%
      \newfontfamily\arabicfont[Path=../fonts/,Script=Arabic]{DejaVuSans.ttf}%
    }{\newfontfamily\arabicfont[Script=Arabic]{DejaVu Sans}}%
  }%
}
\theoremstyle{definition}
\newtheorem{proposition}{Proposition}
\newtheorem{lemma}{Lemma}
\newtheorem{theorem}{Theorem}
\emergencystretch=2em
\raggedbottom
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
'''+macro_defs+r'''\title{'''+text(raw_supp_title)+r'''}
\author{[Author Name]}
\date{}
\begin{document}
\maketitle
\setcounter{tocdepth}{1}
\tableofcontents
\clearpage
'''
    author_metadata=here/'direct_replacements/author_metadata.json'
    if author_metadata.exists():
        author_name=esc(json.loads(author_metadata.read_text())['name'])
        preamble=preamble.replace('[Author Name]',author_name)
    body=crossrefs('\n\n'.join(out)+'\n')
    cited_supp=sorted({int(n) for grp in re.findall(r'\\cite\{([^}]+)\}', body) for n in re.findall(r'ref(\d+)', grp)})
    ref_map=dict(refs)
    assert set(cited_supp) <= set(ref_map), (cited_supp, set(ref_map))
    supp_bibliography=typeset_paragraphs(
        '\\begin{thebibliography}{99}\n'
        + '\n'.join(f'\\bibitem[{n}]{{ref{n}}} {ref_map[n]}' for n in cited_supp)
        + '\n\\end{thebibliography}\n'
    )
    ref_toc='References ([4], [16], [24]--[29] match main manuscript; [30]--[34] supplement-only)'
    ref_heading='References {\\normalsize\\normalfont([4], [16], [24]--[29] match main manuscript; [30]--[34] supplement-only)}'
    emit('main.tex',preamble+'\\input{body}\n\\bigskip\n\\Needspace{6\\baselineskip}\n\\renewcommand{\\refname}{'+ref_heading+'}\n\\phantomsection\\addcontentsline{toc}{section}{'+ref_toc+'}\n\\input{references}\n\\end{document}\n')
    emit('body.tex',body)
    emit('references.tex',supp_bibliography)
    emit('source_manifest.json',json.dumps({'source':'../SUPPLEMENT_EN.md','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'main_source_sha256':hashlib.sha256((here/'MANUSCRIPT_EN.md').read_bytes()).hexdigest(),'tables':table_count,'references':len(cited_supp),'reference_numbers':cited_supp,'table_of_contents':True,'sections':section_headings,'language':'English with verbatim multilingual probes','source_fonts':['Latin Modern','STHeiti Medium','Arial','DejaVu Sans']},indent=2)+'\n')
    return cited_supp
