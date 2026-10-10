import{a as s}from"./index-Ble_6Ww_.js";const o={list:t=>s.get("/posts",{params:t}).then(e=>e.data),get:t=>s.get(`/posts/${t}`).then(e=>e.data),create:t=>s.post("/posts",t).then(e=>e.data),update:(t,e)=>s.post(`/posts/${t}`,e).then(a=>a.data),delete:t=>s.delete(`/posts/${t}`).then(e=>e.data)};export{o as p};
//# sourceMappingURL=posts-BBQo9PdV.js.map
