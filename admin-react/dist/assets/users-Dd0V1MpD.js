import{a as s}from"./index-DgBwYP8a.js";const d={list:()=>s.get("/users").then(e=>e.data),get:e=>s.get(`/users/${e}`).then(t=>t.data),create:e=>s.post("/users",e).then(t=>t.data),update:(e,t)=>s.post(`/users/${e}`,t).then(a=>a.data),delete:e=>s.delete(`/users/${e}`).then(t=>t.data)};export{d as u};
//# sourceMappingURL=users-Dd0V1MpD.js.map
