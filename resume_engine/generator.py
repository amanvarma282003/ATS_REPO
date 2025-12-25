import requests
import os
from uuid import uuid4
from django.conf import settings
from typing import Dict, Any


class ResumeGenerator:
    """
    Resume generation engine.
    Manages LaTeX templates and PDF compilation via external service.
    """
    
    def __init__(self):
        self.latex_service_url = settings.LATEX_SERVICE_URL
        self.storage_path = settings.RESUME_STORAGE_PATH
    
    def get_base_template(self) -> str:
        """
        Return the base LaTeX resume template with placeholders.
        Uses the professional template from template.tex.
        """
        return r"""
\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{fontawesome5}
\usepackage{multicol}
\usepackage{graphicx}
\setlength{\multicolsep}{-3.0pt}
\setlength{\columnsep}{-1pt}
\input{glyphtounicode}

\RequirePackage{tikz}
\RequirePackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{svg.path}

\definecolor{cvblue}{HTML}{0E5484}
\definecolor{black}{HTML}{130810}
\definecolor{darkcolor}{HTML}{0F4539}
\definecolor{cvgreen}{HTML}{3BD80D}
\definecolor{taggreen}{HTML}{00E278}
\definecolor{SlateGrey}{HTML}{2E2E2E}
\definecolor{LightGrey}{HTML}{666666}
\colorlet{name}{black}
\colorlet{tagline}{darkcolor}
\colorlet{heading}{darkcolor}
\colorlet{headingrule}{cvblue}
\colorlet{accent}{darkcolor}
\colorlet{emphasis}{SlateGrey}
\colorlet{body}{LightGrey}

\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1.19in}
\addtolength{\topmargin}{-.7in}
\addtolength{\textheight}{1.4in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{1.0\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{\large#1} & \textbf{\small #2} \\
      \textit{\large#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{1.001\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & \textbf{\small #2}\\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemi{$\vcenter{\hbox{\tiny$\bullet$}}$}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.0in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\newcommand{\resumeSubheadingInline}[3]{
  \item \textbf{#1} -- \textit{#2} \hfill \textit{#3}
}
\newcommand{\resumeItemCompact}[1]{
  \item {\small #1}
}
\newcommand{\resumeItemListStartCompact}{\begin{itemize}[leftmargin=0.15in, topsep=0pt, partopsep=0pt, itemsep=1pt]}
\newcommand{\resumeItemListEndCompact}{\end{itemize}}

\begin{document}

%----------HEADER----------
\begin{center}
    {\Huge \scshape {{CANDIDATE_NAME}}} \\[2pt]
    \small {{CONTACT_INFO}}
\end{center}
\vspace{-8pt}

%-----------SUMMARY----------
\section*{Summary}
\small
{{SUMMARY_BLOCK}}

%-----------EXPERIENCE / PROJECTS----------
\section{Projects}
\resumeSubHeadingListStart
{{PROJECTS_BLOCK}}
\resumeSubHeadingListEnd

%-----------TECHNICAL SKILLS----------
\section*{Technical Skills}
\small
{{SKILLS_BLOCK}}

{{TOOLS_BLOCK}}

\end{document}
"""
    
    def fill_template(self, template: str, placeholders: Dict[str, str]) -> str:
        """
        Fill LaTeX template with placeholder content.
        
        Args:
            template: LaTeX template string
            placeholders: Dictionary mapping placeholder names to content
        
        Returns:
            Filled LaTeX content
        """
        filled_template = template
        
        for placeholder, content in placeholders.items():
            placeholder_tag = f"{{{{{placeholder}}}}}"
            filled_template = filled_template.replace(placeholder_tag, content)
        
        return filled_template
    
    def escape_latex(self, text: str) -> str:
        """
        Escape LaTeX special characters.
        """
        if not text:
            return ''
        
        # IMPORTANT: Escape backslash FIRST to avoid double-escaping
        text = text.replace('\\', r'\textbackslash{}')
        
        replacements = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
        }
        
        for char, escaped in replacements.items():
            text = text.replace(char, escaped)
        
        return text
    
    def compile_latex_to_pdf(self, latex_content: str, output_filename: str) -> str:
        """
        Compile LaTeX to PDF using external service.
        
        Args:
            latex_content: LaTeX document content
            output_filename: Desired filename for PDF
        
        Returns:
            Path to generated PDF file
        
        Raises:
            Exception if compilation fails
        """
        try:
            # Prepare file for upload
            files = {
                'file': (
                    'resume.tex',
                    latex_content.encode('utf-8'),
                    'application/x-tex'
                )
            }
            
            # Call LaTeX service
            response = requests.post(
                self.latex_service_url,
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                # Save PDF to storage
                pdf_path = os.path.join(self.storage_path, output_filename)
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                return pdf_path
            else:
                # Compilation failed
                error_message = response.text
                raise Exception(f"LaTeX compilation failed: {error_message}")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to LaTeX service: {str(e)}")
    
    def generate_resume(self, candidate_data: Dict[str, Any],
                       latex_content: str,
                       candidate_id: int) -> Dict[str, str]:
        """
        Generate complete resume PDF from full LaTeX document.
        
        Args:
            candidate_data: Candidate profile information (for metadata)
            latex_content: Complete LaTeX document string
            candidate_id: Candidate profile ID
        
        Returns:
            Dictionary with resume_id and pdf_path
        """
        # Generate unique resume ID
        resume_id = str(uuid4())
        
        # Generate PDF filename
        pdf_filename = f"{candidate_id}/{resume_id}.pdf"
        
        # Compile LaTeX document to PDF using external service
        pdf_path = self.compile_latex_to_pdf(latex_content, pdf_filename)
        
        return {
            'resume_id': resume_id,
            'pdf_path': pdf_path
        }


# Singleton instance
resume_generator = ResumeGenerator()
