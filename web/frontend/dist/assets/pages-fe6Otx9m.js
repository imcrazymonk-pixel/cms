import{a}from"./index-4bUo0ePp.js";const g={list:()=>a.get("/pages").then(e=>e.data),get:e=>a.get(`/pages/${e}`).then(t=>t.data),create:e=>a.post("/pages",e).then(t=>t.data),update:(e,t)=>a.post(`/pages/${e}`,t).then(p=>p.data),delete:e=>a.delete(`/pages/${e}`).then(t=>t.data)};export{g as p};
//# sourceMappingURL=pages-fe6Otx9m.js.map
