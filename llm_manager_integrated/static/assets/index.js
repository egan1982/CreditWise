(function(){const r=document.createElement("link").relList;if(r&&r.supports&&r.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))s(e);new MutationObserver(e=>{for(const o of e)if(o.type==="childList")for(const a of o.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&s(a)}).observe(document,{childList:!0,subtree:!0});function n(e){const o={};return e.integrity&&(o.integrity=e.integrity),e.referrerPolicy&&(o.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?o.credentials="include":e.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function s(e){if(e.ep)return;e.ep=!0;const o=n(e);fetch(e.href,o)}})();const d="/llm-manager/api";async function i(){try{console.log("正在加载渠道，API地址:",d+"/manage/channels");const t=await fetch(`${d}/manage/channels`);if(!t.ok){console.error("请求失败，状态码:",t.status),l(`请求失败，状态码: ${t.status}`);return}const r=await t.json();if(console.log("API响应:",r),r.code===0){const n=r.data||[];if(n.length===0)document.getElementById("channels-list").innerHTML=`
                    <div class="empty-state bg-white rounded-lg shadow-md p-6 mb-5">
                        <div class="text-4xl mb-2">📡</div>
                        <div class="text-lg font-medium mb-2">暂无渠道</div>
                        <div class="text-gray-600">点击"新建渠道"添加第一个渠道</div>
                    </div>
                `;else{let s='<table class="table border-collapse border border-gray-200 w-full"><thead><tr><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">名称</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">类型</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">模型</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">状态</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">操作</th></tr></thead><tbody>';n.forEach(e=>{s+=`
                        <tr>
                            <td class="border border-gray-200 px-4 py-2">${e.name}</td>
                            <td class="border border-gray-200 px-4 py-2">${e.type}</td>
                            <td class="border border-gray-200 px-4 py-2">${e.models}</td>
                            <td class="border border-gray-200 px-4 py-2">
                                <button 
                                    class="btn ${e.status?"bg-green-600 text-white hover:bg-green-700":"bg-gray-200 text-gray-800 hover:bg-gray-300"} px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" 
                                    onclick="toggleChannelStatus(${e.id}, ${e.status})"
                                    title="${e.status?"点击禁用此渠道（将停用所有渠道）":"点击启用此渠道（将自动禁用其他渠道）"}"
                                >
                                    ${e.status?"✓ 已启用":"○ 已禁用"}
                                </button>
                            </td>
                            <td class="border border-gray-200 px-4 py-2">
                                <button class="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" onclick="testChannel(${e.id})">测试</button>
                                <button class="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" onclick="editChannel(${e.id})">编辑</button>
                                <button class="bg-red-600 text-white hover:bg-red-700 px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" onclick="deleteChannel(${e.id})">删除</button>
                            </td>
                        </tr>
                    `}),s+="</tbody></table>",document.getElementById("channels-list").innerHTML=s}}else{console.error("API返回错误:",r);const n=r.message||r.detail||"未知错误";l("加载渠道失败: "+n)}}catch(t){console.error("请求异常:",t);const r=t.message||t||"未知错误";l("加载渠道异常: "+r)}}function l(t){console.error("错误信息:",t),alert(t)}window.addEventListener("load",()=>{i()});
