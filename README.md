# ResMe: AI Resume Tailoring Pipeline

ResMe is an automated resume generation engine that tailors your project bullets to match specific job descriptions using the Gemini API. It produces clean, ATS-compliant, and highly professional LaTeX (`.tex`) resume source files.

## 🚀 How It Works

The engine uses a base JSON profile (`resume.json`) as the source of truth. It reads target job descriptions from the `jobs/` folder, leverages the Gemini API to custom-tailor the bullet points of your projects to highlight relevant skills, and injects the updated data into a sleek LaTeX template.

---

## 🛠️ Setup & Configuration

1. **Environment Setup**:
   Ensure you are using the provided Python virtual environment:
   ```powershell
   venv\Scripts\activate
   ```

2. **API Configuration**:
   The engine requires a Gemini API key. Make sure your `.env` file in the root directory contains:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

---

## 📖 Usage Guide

### Step 1: Update Your Base Profile
Open `resume.json`. This file acts as your master profile. Update your contact info, education, skills, base projects, experience, and awards here.

### Step 2: Add Job Descriptions
1. Copy the text of the job description you are applying for (e.g., from LinkedIn or the company website).
2. Create a new `.txt` file in the `jobs/` directory. Give it a descriptive name (e.g., `google_backend_intern.txt`).
3. Paste the job description text into the file and save it.

*Note: You can drop as many `.txt` files in the `jobs/` directory as you want. The engine will process all of them sequentially.*

### Step 3: Run the Engine
Run the main script to process the job files:
```powershell
python engine.py
```
**What happens under the hood:**
* The script loops through every text file in the `jobs/` directory.
* It sends your base projects and the job description to Gemini to customize the bullet points.
* It cleans up the AI's response (removing unwanted gaps/spacing).
* It automatically escapes special LaTeX characters (like `&`, `%`, `_`) so the compiler doesn't crash.
* It saves a tailored `.tex` file in the `output_resumes/` folder.

### Step 4: Convert to PDF
Navigate to the `output_resumes/` directory to find your tailored resumes (e.g., `Soham_Shirke_google_backend_intern.tex`). 

To generate the final PDF, you have two options:
* **Overleaf (Recommended & Easiest)**: Copy the contents of the `.tex` file and paste it into a new project on [Overleaf.com](https://www.overleaf.com/). It will compile the PDF automatically.
* **Local Compiler**: If you have a LaTeX distribution installed (like MiKTeX or TeX Live), you can compile it via the command line:
  ```powershell
  pdflatex output_resumes\Soham_Shirke_google_backend_intern.tex
  ```

---

## 📁 Directory Structure
* `engine.py`: The core automation pipeline.
* `resume.json`: Your master profile data.
* `template.tex`: The highly professional ATS-friendly LaTeX template layout.
* `jobs/`: Drop your `.txt` job descriptions in here.
* `output_resumes/`: The engine saves your customized `.tex` resumes here.
* `venv/`: Your local Python dependencies.
