% HustGraduPaper.cls
% author: Weierstras (zhengxinx@qq.com)
% updates:
%   > 2023/02/19 v3.0.1 update:
%     - sort citations in order or appearance.
%     - remove spaces after citations.
%     - add support for `thebibliography'.
%     - number theorem environments continuously.
%     - number environments globally in proposal and translation mode.
%   > 2023/02/20 v3.0.2 update:
%     - add cover templates (by Kelin).
%   > 2023/02/21 v3.0.3 update:
%     - add the support to the graduate report
%     - fix a number of formatting issues(by SukunaShinmyoumaru).

\NeedsTeXFormat{LaTeX2e}

\def\HGP@name{hust}
\def\HGP@date{2023/02/20}
\def\HGP@version{v3.0.2}
\def\HGP@introduction{zx version}
\ProvidesClass{\HGP@name}[\HGP@date~\HGP@version~\HGP@introduction]


\LoadClass[a4paper]{article}
\RequirePackage[AutoFakeBold=2,AutoFakeSlant=true]{xeCJK}
\RequirePackage[zihao=-4,UTF8,heading=true,fontset=none]{ctex}
\RequirePackage{template/packages}


%====================== 参数 ======================%
\def\HGP@mode{thesis}
\DeclareOption{thesis}{\def\HGP@mode{thesis}}           % 论文
\DeclareOption{proposal}{\def\HGP@mode{proposal}}       % 开题报告
\DeclareOption{translation}{\def\HGP@mode{translation}} % 文献翻译
\DeclareOption{graduatereport}{\def\HGP@mode{graduatereport}} % 研究生报告

\DeclareOption{biblatex}{\def\HGP@biblatex}             % 使用 biblatex 

\ProcessOptions
\ExecuteOptions{thesis}
\relax


%===================== 宏定义 =====================%
\newcommand{\sectionUnnumbered}[1]{
    \section*{#1}
    \addcontentsline{toc}{section}{#1}
}
\newcommand{\keywordsch}{{\noindent\zihao{4}\bfseries 关键词：}}
\newcommand{\keywordsen}{{\noindent\zihao{4}\bfseries Keywords: }}

% 原创页
\RequirePackage{template/authorization}

% 封面
% \def\@school{计算机科学与技术}
\newcommand{\school}[1]{\def\@school{#1}}
\newcommand{\classnum}[1]{\def\@classnum{#1}}
\newcommand{\stunum}[1]{\def\@stunum{#1}}
\newcommand{\instructor}[1]{\def\@instructor{#1}}
\RequirePackage{template/cover/cover}

% 中文摘要标题
\newcommand{\abstractch}{
    \IfStrEqCase{\HGP@mode}{
        {proposal}{}
        {translation}{{\noindent\bf\zihao{4}摘要：}}
        {thesis}{\sectionUnnumbered{摘\hspace{1em}要}}
    }
}

% 英文摘要标题
\newcommand{\abstracten}{
    \IfStrEqCase{\HGP@mode}{
        {proposal}{}
        {translation}{{\noindent\bf\zihao{4}Abstract: }}
        {thesis}{\sectionUnnumbered{Abstract}\sloppy}
    }
}

% 致谢标题
\newcommand{\acknowledgement}{%
    \ifdefstring{\HGP@mode}{thesis}{%
        \sectionUnnumbered{致\hspace{1em}谢}%
    }{%
        \sectionUnnumbered{致谢}%
    }%
}

% 文献翻译结尾插入原文
\newcommand{\originalart}[1]{
    \clearpage
    \begin{table}[h]
    \vspace{240pt}
    \centerline{\bf\zihao{3}参考文献原文}
    \end{table}
    \clearpage
    \includepdf[pages=-]{#1}
}


%====================== 字体 ======================%
\IfFontExistsTF{SimSun}{
    \setCJKmainfont[
        BoldFont={SimHei},
        ItalicFont={KaiTi}
    ]{SimSun}
    \setCJKsansfont{SimHei}
    \setCJKmonofont{FangSong}
    \setCJKfamilyfont{zhsong}{SimSun}
    \setCJKfamilyfont{zhhei}{SimHei}
    \setCJKfamilyfont{zhkai}{KaiTi}
    \setCJKfamilyfont{zhfs}{FangSong}
}{
    \setCJKmainfont[
        BoldFont={FandolHei-Regular},
        ItalicFont={FandolKai-Regular}
    ]{FandolSong-Regular}
    \setCJKsansfont{FandolHei-Regular}
    \setCJKmonofont{FandolFang-Regular}
    \setCJKfamilyfont{zhsong}{FandolSong-Regular}
    \setCJKfamilyfont{zhhei}{FandolHei-Regular}
    \setCJKfamilyfont{zhkai}{FandolKai-Regular}
    \setCJKfamilyfont{zhfs}{FandolFang-Regular}
}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\providecommand{\songti}{\CJKfamily{zhsong}}
\providecommand{\heiti}{\CJKfamily{zhhei}}
\providecommand{\kaishu}{\CJKfamily{zhkai}}
\providecommand{\fangsong}{\CJKfamily{zhfs}}


%==================== 标题格式 ====================%
\IfStrEqCase{\HGP@mode}{
    {translation}{
        \ctexset{
            section={format={\raggedright\bfseries\zihao{4}}},
            subsection={format={\bfseries\zihao{-4}}},
            subsubsection={format={\bfseries\zihao{-4}}}
        }
    }
    {proposal}{
        \ctexset{
            section={
                name={,、},
                aftername=\hspace{0pt},
                number={\chinese{section}},
                format={\raggedright\bfseries\zihao{4}}
            },
            subsection={format={\bfseries\zihao{-4}}},
            subsubsection={format={\bfseries\zihao{-4}}}
        }
    }
    {thesis}{
        \ctexset{
            section={format={\centering\bfseries\zihao{-2}}},
            subsection={format={\bfseries\zihao{4}}},
            subsubsection={format={\bfseries\zihao{-4}}}
        }
    }
    {graduatereport}{
        \ctexset{
            section={format={\centering\bfseries\zihao{-2}}},
            subsection={format={\bfseries\zihao{4}}},
            subsubsection={format={\bfseries\zihao{-4}}}
        }
    }
}

% 图表标题格式
\DeclareCaptionFont{hust}{\heiti\zihao{-4}}
\DeclareCaptionFont{husttable}{\heiti\zihao{5}}
\DeclareCaptionFont{hustalgorithm}{\zihao{5}}
\captionsetup{labelsep=quad}
\captionsetup{font=hust}
\captionsetup[figure]{position=bottom,skip={6pt}}
\captionsetup[table]{font=husttable,position=top,skip={0pt}}
\captionsetup[algorithm]{font=hustalgorithm,labelfont=bf,labelsep=space,justification=raggedright,singlelinecheck=false,position=top,skip={0pt}}
\setlength{\belowcaptionskip}{0pt}
\setlength{\intextsep}{0pt plus 2pt}
\AtBeginEnvironment{table}{\vspace{0.5\baselineskip}}
\AtBeginEnvironment{algorithm}{\vspace{0.5\baselineskip}}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}


%==================== 页面格式 ====================%
% 页边距
\geometry{left=1.25in,right=1.25in,top=1.4in,bottom=1.4in}
\geometry{headsep=1em,footskip=3em}
\geometry{headheight=37.1pt}

\setstretch{1.625}              % 行间距 (latex=word*13/12)
% \setlength{\parskip}{3pt}       % 段间距
% \setlength{\parindent}{0.0in}   % 段落缩进

\pagestyle{fancy}
\fancyhf{}
\definecolor{headblue}{RGB}{46,116,181}

% 设置页眉样式
\def\HGP@header{
    \IfStrEqCase{\HGP@mode}{
        {translation}{\ziju{0.5}毕业设计（论文）参考文献译文}
        {proposal}{华中科技大学本科生毕业设计（论文）开题报告}
        {thesis}{\ziju{1}华中科技大学毕业设计}
        {graduatereport}{\ziju{1}华中科技大学研究生课程报告}
    }
}
\fancyhead[C]{\textcolor[RGB]{192,0,0}{
    \kaishu\bfseries\zihao{3}\HGP@header
}}
\def\headrule{
    {
        \if@fancyplain\let\headrulewidth\plainheadrulewidth\fi
        \vspace*{1mm}
        {\color{headblue}\hrule\@height 0.5pt\@width\headwidth\vskip1pt}
        {\color{headblue}\hrule\@height 0.5pt\@width\headwidth}
        \vskip-2\headrulewidth\vskip-1pt
    }
    \vspace{36pt}
}

% 设置页脚样式
\fancyfoot[L]{\textcolor{headblue}{\rule[3pt]{6.7cm}{0.4pt}}}
\fancyfoot[C]{\zihao{5}\thepage}
\fancyfoot[R]{\textcolor{headblue}{\rule[3pt]{6.7cm}{0.4pt}}}

% 设置页眉页脚位置
\usepackage{geometry}  
\geometry{a4paper,bottom=25mm}
\setlength{\voffset}{-3mm}                        
\setlength{\footskip}{30pt}


%==================== 引用相关 ====================%
\hypersetup{hidelinks}

% 按章编号
\newcommand{\HGP@setcounter}[1]{
    \ifdefstring{\HGP@mode}{thesis}{
        \expandafter\renewcommand\csname the#1\endcsname{\thesection-\arabic{#1}}
        \@addtoreset{#1}{section}
    }{}
}
\HGP@setcounter{figure}
\HGP@setcounter{table}
\HGP@setcounter{equation}
\HGP@setcounter{algorithm}

% autoref
\def\equationautorefname{式}
\def\algorithmautorefname{算法}
\def\footnoteautorefname{注}
\def\itemautorefname{项}
\def\figureautorefname{图}
\def\tableautorefname{表}
\def\appendixautorefname{附录}
\def\sectionautorefname{节}
\def\subsectionautorefname{节}
\def\paragraphautorefname{段落}
\def\subparagraphautorefname{子段落}


%==================== 定理环境 ====================%
\newtheorem{theorem}{定理}
\HGP@setcounter{theorem}
\def\theoremautorefname{定理}

\newcommand{\HGP@newtheorem}[2]{
    \newtheorem{#1}[theorem]{#2}    % 创建定理环境
    % \HGP@setcounter{#1}             % 按章编号
    \expandafter\def\csname #1autorefname\endcsname{#2} % autoref
}
\HGP@newtheorem{example}{例}
\HGP@newtheorem{definition}{定义}
\HGP@newtheorem{axiom}{公理}
\HGP@newtheorem{property}{性质}
\HGP@newtheorem{proposition}{命题}
\HGP@newtheorem{lemma}{引理}
\HGP@newtheorem{corollary}{推论}
\HGP@newtheorem{remark}{注解}
\HGP@newtheorem{condition}{条件}
\HGP@newtheorem{conclusion}{结论}
\HGP@newtheorem{assumption}{假设}
\HGP@newtheorem{fact}{事实}
\renewcommand{\proofname}{证明}


%==================== 目录格式 ====================%
\setcounter{tocdepth}{2}
\tocloftpagestyle{fancy}
\renewcommand{\cfttoctitlefont}{\hfill\bfseries\zihao{-2}}
\renewcommand{\contentsname}{目\hspace{1em}录}
\renewcommand{\cftaftertoctitle}{\hfill}
\renewcommand{\cftafterloftitleskip}{12pt}
\renewcommand{\cftdotsep}{0.75}
\renewcommand{\cftsecdotsep}{\cftdotsep}    % 设置 Section 引导点
\renewcommand{\cftbeforesecskip}{3pt}       % 设置段间距


%==================== 列表格式 ====================%
\newcommand*{\circled}[1]{\lower.7ex\hbox{\tikz\draw (0pt, 0pt)%
    circle (.45em) node {\makebox[1em][c]{\small #1}};}}
\robustify{\circled}
\newlength{\HGP@enumlabelwidth}
\settowidth{\HGP@enumlabelwidth}{(9)}
\newlength{\HGP@enumlabelsep}
\setlength{\HGP@enumlabelsep}{0.5em}

\setenumerate[1]{
    label=(\arabic*),
    align=left,
    labelwidth=\HGP@enumlabelwidth,
    labelsep=\HGP@enumlabelsep,
    leftmargin=0pt,
    itemindent=\dimexpr\parindent+\HGP@enumlabelwidth+\HGP@enumlabelsep\relax,
    listparindent=\parindent,
    itemsep=0pt,
    partopsep=0pt,
    parsep=0pt,
    topsep=0pt
}
\setenumerate[2]{
    label=\circled{\arabic*},
    labelindent=\parindent,
    leftmargin=*,
    itemsep=0pt,
    partopsep=0pt,
    parsep=0pt,
    topsep=0pt
}
\setenumerate[3]{
    label=\Alph*.,
    labelindent=\parindent,
    leftmargin=*,
    itemsep=0pt,
    partopsep=0pt,
    parsep=0pt,
    topsep=0pt
}
\setitemize{
    label=\textbullet,
    labelindent=\parindent,
    leftmargin=*,
    itemsep=0pt,
    partopsep=0pt,
    parsep=0pt,
    topsep=0pt
}
\setdescription{
    labelindent=\parindent,
    leftmargin=*,
    itemsep=0pt,
    partopsep=0pt,
    parsep=0pt,
    topsep=0pt
}


%==================== 代码格式 ====================%
\definecolor{shadecolor}{gray}{0.88}
\DefineVerbatimEnvironment{cppcode}{Verbatim}{
    framesep=4pt,
    fontsize=\fontsize{11pt}{13.2pt}\selectfont,
    fontshape=it
}
\DefineVerbatimEnvironment{pythoncode}{Verbatim}{
    framesep=4pt,
    fontsize=\fontsize{11pt}{13.2pt}\selectfont,
    fontshape=it
}

%================== tikz & plots ==================%
\pgfplotsset{compat=1.17}
\usetikzlibrary{quotes,angles}
\usetikzlibrary{shapes,arrows,positioning}

\newlength\tikzboxwidth
\newlength\tikzboxheight
\newcommand\tikzbox[1]{
    \settowidth\tikzboxwidth{#1}
    \settoheight\tikzboxheight{#1}
    \begin{tikzpicture}
        \path[use as bounding box]
            (-0.5\tikzboxwidth,-0.5\tikzboxheight)rectangle
            (0.5\tikzboxwidth,0.5\tikzboxheight);
        \node[inner sep=\tabcolsep+0.5\arrayrulewidth,line width=0.5mm,draw=black]
            at(0,0){#1};
    \end{tikzpicture}
}


%====================== 算法 ======================%
\floatstyle{ruled}
\restylefloat{algorithm}
\floatname{algorithm}{算法}
\renewcommand{\algorithmicrequire}{\textbf{输入：}}
\renewcommand{\algorithmicensure}{\textbf{输出：}}
\algrenewcommand\algorithmicindent{1.5em}
\algrenewcommand\alglinenumber[1]{\zihao{5}#1:}

\AtBeginEnvironment{algorithm}{\zihao{5}}
\AtBeginEnvironment{algorithmic}{\vspace{1pt}\zihao{5}\setstretch{1.0}}
\AtEndEnvironment{algorithmic}{\vspace{1pt}}


%================== 参考文献 ==================%
\ifdefined\HGP@biblatex
    \ExecuteBibliographyOptions{
        sorting=none,
        maxbibnames=3,
        minbibnames=3,
        gbnamefmt=familyahead,
        gbfieldtype=false,
        url=false,
        doi=false,
        eprint=false
    }
    \newcommand{\references}{
        \printbibliography[heading=bibintoc,title=参考文献]
        \ifdefstring{\HGP@mode}{thesis}{\clearpage}{}
    }
\else
    \newcommand{\references}[1][]{
        \addcontentsline{toc}{section}{参考文献}
        \ifthenelse{\isempty{#1}}{}{
            \bibliographystyle{unsrt}
            \bibliography{#1}
        }
        \ifdefstring{\HGP@mode}{thesis}{\clearpage}{}
    }
\fi


%==================== 上标引用 ====================%
\let\normalcite\cite
\DeclareRobustCommand{\cite}[2][]{%
    \unskip\textsuperscript{~\ifblank{#1}{\normalcite{#2}}{\normalcite[#1]{#2}}}%
    \unskip%
}

%==================== 图片引用 ====================%
\newcommand{\cfig}[3]{
  \begin{figure}[htb]
    \centering
    \setlength{\abovecaptionskip}{0.4cm} %增大caption和图像之间的距离
    \setlength{\belowcaptionskip}{-0.4cm} %缩小caption和下方文字的距离
    \includegraphics[width=#2\textwidth]{images/#1.png}
    \caption{#3}
    \label{fig:#1}
  \end{figure}
}
% \usepackage{paralist}
% \let\itemize\compactitem
% \let\enditemize\endcompactitem
% \let\enumerate\compactenum
% \let\endenumerate\endcompactenum
% \let\description\compactdesc
% \let\enddescription\endcompactdesc
\tolerance=1
\emergencystretch=\maxdimen
\hyphenpenalty=10000
\exhyphenpenalty=10000
\hbadness=10000

\usepackage[]{titlesec}
\setcounter{secnumdepth}{4}
\newlength{\HGP@subtitleskip}
\setlength{\HGP@subtitleskip}{0.25\baselineskip}
\titlespacing{\subsection}{0pt}{\HGP@subtitleskip}{\HGP@subtitleskip}
\titlespacing{\subsubsection}{0pt}{\HGP@subtitleskip}{\HGP@subtitleskip}
\titleformat{\paragraph}[hang]{\bfseries\zihao{-4}}{\theparagraph}{1em}{}
\titlespacing{\paragraph}{0pt}{\HGP@subtitleskip}{\HGP@subtitleskip}

\usepackage{geometry}
\geometry{footskip = 15pt,textwidth = 400pt,headsep = 0pt}
\floatname{algorithm}{算法}
%定义了新的长度变量名为\bibitemsep，文献名之间的行距
\setlength{\bibitemsep}{.01\baselineskip plus .005\baselineskip minus .005\baselineskip}
%定义新的长度变量名为\bibparskip，文献内部的行距
\newlength{\bibparskip}\setlength{\bibparskip}{0pt}
%用\let命令将原先的\thebibliography保存为\oldthebibliography
\let\oldthebibliography\thebibliography
%然后重新定义\thebibliography命令
\renewcommand\thebibliography[1]{%
  \oldthebibliography{#1}%#1
  \setlength{\parskip}{\bibitemsep}%
  \setlength{\itemsep}{\bibparskip}%
}

%==================== 算法跨页 ====================%
\makeatletter
\newenvironment{breakablealgorithm}
  {% \begin{breakablealgorithm}
   \begin{center}
     \refstepcounter{algorithm}% New algorithm
     \hrule height.8pt depth0pt \kern2pt% \@fs@pre for \@fs@ruled
     \renewcommand{\caption}[2][\relax]{% Make a new \caption
       {\raggedright\textbf{\ALG@name~\thealgorithm} ##2\par}%
       \ifx\relax##1\relax % #1 is \relax
         \addcontentsline{loa}{algorithm}{\protect\numberline{\thealgorithm}##2}%
       \else % #1 is not \relax
         \addcontentsline{loa}{algorithm}{\protect\numberline{\thealgorithm}##1}%
       \fi
       \kern2pt\hrule\kern2pt
     }
  }{% \end{breakablealgorithm}
     \kern2pt\hrule\relax% \@fs@post for \@fs@ruled
   \end{center}
  }
\makeatother
