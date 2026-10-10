import{a as e}from"./index-HYaFhjMp.js";const o={list:()=>e.get("/media").then(a=>a.data),upload:a=>e.post("/media/upload",a,{headers:{"Content-Type":"multipart/form-data"}}).then(t=>t.data),delete:a=>e.post("/media/delete",{path:a}).then(t=>t.data)};export{o as m};
//# sourceMappingURL=media-BeTY6S1r.js.map
