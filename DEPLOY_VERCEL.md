# How to Deploy to Vercel via GitHub (Live Web App)

Follow these 3 simple steps to make your tool live on Vercel so anyone in the world can use it from any device (Mobile, Mac, Windows):

---

### Step 1: Create a GitHub Repository

1. Open your browser and go to: **[https://github.com/new](https://github.com/new)**
2. Enter a repository name (e.g., `image-pdf-studio`).
3. Set the repository to **Public** (or Private).
4. **Do not** initialize with README or .gitignore (we already have them ready!).
5. Click **"Create repository"**.

---

### Step 2: Push Your Local Code to GitHub

Open terminal / PowerShell in this folder and run these 2 commands (replace `<your-username>` with your GitHub username):

```bash
git remote add origin https://github.com/<your-username>/image-pdf-studio.git
git push -u origin main
```

*(If prompted, log in with your GitHub credentials or Personal Access Token).*

---

### Step 3: Connect to Vercel (1-Click Deployment)

1. Open **[https://vercel.com/new](https://vercel.com/new)**
2. Sign in with your GitHub account.
3. You will see your newly pushed repository `image-pdf-studio`. Click **"Import"**.
4. Leave all build settings as default (Framework Preset: **Other** / Static).
5. Click **"Deploy"**.

---

### 🎉 Congratulations!
Within 30 seconds, Vercel will give you a live production URL:
`https://image-pdf-studio.vercel.app`

### Why this is 100% Free and Fast on Vercel:
- **Zero Server Costs:** All PDF and image manipulation is processed client-side via high-performance `pdf-lib` and `pdf.js`.
- **No File Size Limits:** Handles large PDFs (10MB, 50MB+) without triggering Vercel's 4.5MB serverless payload limit.
- **100% Privacy:** Files are processed inside the user's browser without uploading to any third-party server.
- **Universal:** Works seamlessly on mobile devices (iOS / Android) and desktop browsers (Chrome, Edge, Safari, Firefox).
