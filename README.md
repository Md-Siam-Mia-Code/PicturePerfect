
# 🌟 PicturePerfect  
## 🚀 AI-Powered Image Upscaler & Enhancer  

<img src="https://github.com/Md-Siam-Mia-Code/PicturePerfect/blob/main/assets/img/PicturePerfect.png" alt="PicturePerfect Logo" width="600"/>  

---

## 🗂️ Table of Contents  
- [📖 Introduction](#-introduction)  
- [✨ Features](#-features)  
- [🛠️ Installation](#-installation)  
- [💻 Usage](#-usage)  
- [🤝 Contributing](#-contributing)  
- [📜 License](#-license)  

---

## 📖 Introduction  
Welcome to **PicturePerfect** – where your blurry, low-res images get a major glow-up! 🌈  

PicturePerfect is an AI-powered image enhancer that transforms your low-quality pics into high-resolution masterpieces. Using cutting-edge deep learning models, it sharpens details, improves colors, and makes your images pop – all with a super slick web interface.  

Say goodbye to pixelation – and hello to perfection! 😎  

---

## ✨ Features  
🔥 **AI Magic:** Sharpens and enhances images using deep learning models.  
⚡ **GPU Boost:** Takes advantage of your GPU (if available) for lightning-fast processing.  
🧪 **Half Precision:** Boosts performance on compatible GPUs.  
🖥️ **Easy Web Interface:** Drag, drop, enhance – it’s that simple!  
🚋 **Batch Processing:** Process multiple images at once like a pro.  
🧱 **Side-by-Side Previews:** Instantly see the difference between original and enhanced images.  
📢 **Real-Time Updates:** Stay in the loop with real-time progress and notifications.  
🏎️ **Quick Downloads:** Save enhanced images individually or as a convenient ZIP file.  
🖱️ **Drag and Drop:** No complicated menus – just drop your files and go!  
💻 **Mobile Friendly:** Works beautifully on both desktop and mobile browsers.  

---

## 🛠️ Installation  
### 📋 Prerequisites  
Before you dive in, make sure you have these installed:  
- 🐉 [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html)  
- 🐍 [Python](https://www.python.org/) 3.7 or Higher  
- 📦 [pip](https://pypi.org/project/pip/) (Python Package Installer)  
- ♨️ [PyTorch](https://pytorch.org/) >= 1.7  
- ➕ [Git](https://git-scm.com/) Installed  
- ❗ [NVIDIA GPU](https://www.nvidia.com/en-us/geforce/graphics-cards/) + [CUDA](https://developer.nvidia.com/cuda-downloads) (Optional)  

### 💾 Steps  
1. **Clone the Repository**  
```bash
git clone https://github.com/Md-Siam-Mia-Code/PicturePerfect.git
cd PicturePerfect
```  

2. **Create a Virtual Environment**  
```bash
conda create -n PicturePerfect python=3.7 -y
conda activate PicturePerfect
```  

3. **Install PyTorch**  
For NVIDIA GPU:  
```bash
conda install pytorch torchvision torchaudio pytorch-cuda=<your_cuda_version> -c pytorch -c nvidia -y
```  
For CPU:  
```bash
conda install pytorch torchvision torchaudio cpuonly -c pytorch -y
```  

4. **Install Dependencies**  
```bash
pip install -r requirements.txt
```  

5. **Run Setup**  
```bash
python setup.py develop
```  

6. **Download Models**  
🚀 *Don't worry – the models will download automatically when you run the app for the first time!*  

---

## 💻 Usage  
### ▶️ Running the App  
Start the server with:  
```bash
uvicorn main:app --host 127.0.0.1 --port 3005
```  

**Access the Web Interface:**  
🌐 Open your browser and visit: [http://127.0.0.1:3005](http://127.0.0.1:3005)

### ▶️ **For one-click RUN**
Edit the run.bat Batch script on your PicturePerfect directory.

    @echo off

    :: Activate the conda environment for PicturePerfect
    CALL "C:\ProgramData\<your anaconda distributation name>\Scripts\activate.bat" PicturePerfect

    :: Navigate to the PicturePerfect directory (Change path according to yours)
    cd /D path/to/your/PicturePerfect

    :: Run PicturePerfect
    uvicorn main:app --host 127.0.0.1 --port 3005

### 📸 How to Enhance Images  
1. **Upload Images:** Drag and drop or select `.jpg`, `.jpeg`, or `.png` files.  
2. **Enhance:** Hit the "✨ Enhance" button and let the magic happen!  
3. **View:** Check out the side-by-side comparison in the preview grid.  
4. **Download:** Save your enhanced images one by one or as a ZIP file.  
5. **Clear:** Wipe out both input and output images in one click.  
6. **Reload:** If anything acts up, just reload the backend.  

---

## 🤝 Contributing  
🎉 **Want to make PicturePerfect even more perfect?**  
1. 🌟 Fork the repository  
2. 📂 Create a new branch (`git checkout -b feature/YourFeature`)  
3. 📝 Commit your changes (`git commit -m 'Add some feature'`)  
4. 📤 Push to the branch (`git push origin feature/YourFeature`)  
5. 🔃 Open a Pull Request – and boom, you're contributing!  

---

## 📜 License  
This project is licensed under the **MIT License** – because good things should be shared. 😎  

---

### 🎨 Emojis & Style Highlights  
🚀 **AI-powered enhancement** – because your pictures deserve the best.  
🛠️ **Easy setup** – because life is too short for complicated installs.  
💻 **Seamless usage** – because nobody likes a clunky interface.  
🤝 **Open for contributions** – because teamwork makes the dream work.  
📜 **Open-source** – because sharing is caring.  

---

# ❤️ *Picture-perfect results, every time!*