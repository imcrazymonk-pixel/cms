import{a}from"./index-CBHfUf-P.js";const i={list:()=>a.get("/categories").then(e=>e.data),get:e=>a.get(`/categories/${e}`).then(t=>t.data),create:e=>a.post("/categories",e).then(t=>t.data),update:(e,t)=>a.post(`/categories/${e}`,t).then(o=>o.data),delete:e=>a.delete(`/categories/${e}`).then(t=>t.data)};export{i as c};
//# sourceMappingURL=categories-DtfzM_j6.js.map
