import os, re, json, shutil, subprocess, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP="Viral Clips Generator"
OUT=os.path.join(os.path.expanduser("~"),"ViralClips")

def ffmpeg_path():
    p=shutil.which("ffmpeg")
    if p: return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def download_video(url, out, log):
    import yt_dlp
    log("Descargando video...")
    os.makedirs(out,exist_ok=True)
    opts={"format":"bv*+ba/b","merge_output_format":"mp4","ffmpeg_location":ffmpeg_path(),
          "outtmpl":os.path.join(out,"source.%(ext)s"),"noplaylist":True,"quiet":True}
    with yt_dlp.YoutubeDL(opts) as y: y.download([url])
    for f in os.listdir(out):
        if f.startswith("source.") and f.lower().endswith((".mp4",".mkv",".webm",".mov")):
            return os.path.join(out,f)
    raise RuntimeError("No se encontró el video descargado.")

def transcribe(video, log):
    from faster_whisper import WhisperModel
    log("Cargando IA de voz. La primera vez puede tardar...")
    model=WhisperModel("small",device="cpu",compute_type="int8")
    log("Transcribiendo audio...")
    segs,info=model.transcribe(video,beam_size=5,vad_filter=True)
    rows=[{"start":float(s.start),"end":float(s.end),"text":s.text.strip()} for s in segs if s.text.strip()]
    if not rows: raise RuntimeError("No se detectó voz.")
    return rows,info.language

def score(text):
    words=re.findall(r"\b[\w']+\b",text.lower())
    triggers=set("secret mistake never always incredible crazy important truth why how best worst money problem learned imagine shocking amazing pero nunca siempre secreto error increíble importante verdad cómo mejor peor dinero problema aprendí".split())
    return sum(w in triggers for w in words)*2 + (text.count("?")+text.count("¿"))*1.4 + min(len(words)/28,1.5)

def find_clips(segs, seconds, limit):
    duration=segs[-1]["end"]; candidates=[]; start=0
    while start<duration:
        end=min(start+seconds,duration)
        parts=[s for s in segs if s["end"]>start and s["start"]<end]
        text=" ".join(s["text"] for s in parts)
        speech=sum(max(0,min(s["end"],end)-max(s["start"],start)) for s in parts)
        if speech>=min(8,seconds*.35) and len(text.split())>=18:
            density=min(len(text.split())/max(end-start,1),4)
            candidates.append({"start":start,"end":end,"text":text,
                               "score":score(text)+density*2+min(speech/max(end-start,1),1)})
        start+=8
    candidates.sort(key=lambda x:x["score"],reverse=True)
    chosen=[]
    for c in candidates:
        if all(abs(c["start"]-x["start"])>=seconds*.65 for x in chosen): chosen.append(c)
        if len(chosen)>=limit: break
    return sorted(chosen,key=lambda x:x["start"])

def stamp(t):
    ms=int(round(t*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(segs,a,b,path):
    lines=[]; n=1
    for s in segs:
        x,y=max(s["start"],a),min(s["end"],b)
        if y<=x: continue
        lines += [str(n),f"{stamp(x-a)} --> {stamp(y-a)}",s["text"],""]; n+=1
    open(path,"w",encoding="utf-8").write("\n".join(lines))

def render(ffmpeg,video,c,segs,n,out,burn):
    mp4=os.path.join(out,f"clip_{n:02}.mp4"); srt=os.path.join(out,f"clip_{n:02}.srt")
    write_srt(segs,c["start"],c["end"],srt)
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if burn:
        path=srt.replace("\\","/").replace(":","\\:")
        vf += ",subtitles='" + path + "'"
    cmd=[ffmpeg,"-y","-ss",str(c["start"]),"-i",video,"-t",str(c["end"]-c["start"]),
         "-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23",
         "-c:a","aac","-b:a","128k","-movflags","+faststart",mp4]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError("FFmpeg no pudo crear el clip:\n"+p.stderr[-1000:])
    return mp4,srt

class App:
 def __init__(self,root):
    self.root=root; root.title(APP); root.geometry("740x570"); root.minsize(650,520)
    self.url=tk.StringVar(); self.file=tk.StringVar(); self.length=tk.IntVar(value=35)
    self.count=tk.IntVar(value=5); self.burn=tk.BooleanVar(value=False)
    frame=ttk.Frame(root,padding=18); frame.pack(fill="both",expand=True)
    ttk.Label(frame,text=APP,font=("Segoe UI",20,"bold")).pack(anchor="w")
    ttk.Label(frame,text="Convierte videos en clips verticales automáticamente.").pack(anchor="w",pady=(2,14))
    box=ttk.LabelFrame(frame,text="Video de YouTube (enlace)",padding=10); box.pack(fill="x",pady=5)
    ttk.Entry(box,textvariable=self.url).pack(fill="x")
    box2=ttk.LabelFrame(frame,text="O selecciona un video de tu computadora",padding=10); box2.pack(fill="x",pady=5)
    row=ttk.Frame(box2); row.pack(fill="x")
    ttk.Entry(row,textvariable=self.file).pack(side="left",fill="x",expand=True)
    ttk.Button(row,text="Examinar",command=self.browse).pack(side="left",padx=6)
    opts=ttk.LabelFrame(frame,text="Configuración",padding=10); opts.pack(fill="x",pady=5)
    row=ttk.Frame(opts); row.pack(anchor="w")
    ttk.Label(row,text="Duración:").pack(side="left")
    ttk.Combobox(row,textvariable=self.length,values=[15,20,30,35,45,60],width=6,state="readonly").pack(side="left",padx=6)
    ttk.Label(row,text="Cantidad máxima:").pack(side="left",padx=(14,0))
    ttk.Combobox(row,textvariable=self.count,values=[3,5,8,10],width=6,state="readonly").pack(side="left",padx=6)
    ttk.Checkbutton(opts,text="Incrustar subtítulos (opcional)",variable=self.burn).pack(anchor="w",pady=6)
    self.btn=ttk.Button(frame,text="ANALIZAR Y GENERAR CLIPS",command=self.start); self.btn.pack(fill="x",pady=10,ipady=7)
    self.status=tk.StringVar(value="Listo."); ttk.Label(frame,textvariable=self.status,wraplength=680).pack(anchor="w")
    self.logbox=tk.Text(frame,height=10,state="disabled",wrap="word"); self.logbox.pack(fill="both",expand=True,pady=6)
    ttk.Label(frame,text="Utiliza únicamente videos propios o con permiso de reutilización.",foreground="#9a5b00").pack(anchor="w")
 def browse(self):
    p=filedialog.askopenfilename(filetypes=[("Videos","*.mp4 *.mov *.mkv *.webm *.avi"),("Todos","*.*")])
    if p:self.file.set(p)
 def log(self,msg): self.root.after(0,self._log,msg)
 def _log(self,msg):
    self.status.set(msg); self.logbox.configure(state="normal"); self.logbox.insert("end",msg+"\n"); self.logbox.see("end"); self.logbox.configure(state="disabled")
 def start(self):
    if not self.file.get().strip() and not self.url.get().strip():
        messagebox.showwarning(APP,"Selecciona un video o pega un enlace."); return
    self.btn.configure(state="disabled"); threading.Thread(target=self.work,daemon=True).start()
 def work(self):
    try:
        os.makedirs(OUT,exist_ok=True); ff=ffmpeg_path(); video=self.file.get().strip()
        if not video: video=download_video(self.url.get().strip(),OUT,self.log)
        segs,lang=transcribe(video,self.log); self.log("Idioma detectado: "+str(lang)+". Buscando momentos...")
        clips=find_clips(segs,self.length.get(),self.count.get())
        if not clips: raise RuntimeError("No se encontraron segmentos hablados suficientes.")
        report=[]
        for i,c in enumerate(clips,1):
            self.log(f"Creando clip {i}/{len(clips)}...")
            mp4,srt=render(ff,video,c,segs,i,OUT,self.burn.get())
            report.append({"video":mp4,"subtitles":srt,"start":c["start"],"end":c["end"],"score":round(c["score"],2),"text":c["text"]})
        with open(os.path.join(OUT,"clips_report.json"),"w",encoding="utf-8") as f: json.dump({"language":lang,"clips":report},f,ensure_ascii=False,indent=2)
        self.log(f"Terminado: {len(report)} clips en {os.path.abspath(OUT)}")
        self.root.after(0,lambda:messagebox.showinfo(APP,"Clips creados en:\n"+os.path.abspath(OUT)))
    except Exception as e:
        self.log("ERROR: "+str(e)); self.root.after(0,lambda:messagebox.showerror(APP,str(e)))
    finally:self.root.after(0,lambda:self.btn.configure(state="normal"))

if __name__=="__main__":
 root=tk.Tk()
 try: ttk.Style().theme_use("vista")
 except: pass
 App(root); root.mainloop()
