import{a}from"./index-Sq-mRiXU.js";const m={list:()=>a.get("/menus").then(e=>e.data),get:e=>a.get(`/menus/${e}`).then(t=>t.data),create:e=>a.post("/menus",e).then(t=>t.data),update:(e,t)=>a.post(`/menus/${e}`,t).then(n=>n.data),delete:e=>a.delete(`/menus/${e}`).then(t=>t.data)};export{m};
//# sourceMappingURL=menus-BtCIkFPV.js.map
