function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
/**
 * LLM Manager 上下文
 * 
 * 提供全局配置和状态管理
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

// 创建默认上下文
var defaultContext = {
  globalHeaders: {},
  globalTheme: {
    primaryColor: '#3498db',
    secondaryColor: '#95a5a6',
    successColor: '#2ecc71',
    dangerColor: '#e74c3c',
    warningColor: '#f39c12',
    textColor: '#333',
    secondaryTextColor: '#666',
    headerBgColor: '#f2f2f2',
    cardBgColor: '#f8f9fa',
    borderColor: '#ddd',
    selectedBgColor: '#e3f2fd',
    detailBgColor: '#f8f9fa'
  },
  globalConfig: {
    pageSize: 20,
    enableNotifications: true,
    apiTimeout: 30000
  },
  // 设置全局配置的方法
  setGlobalHeaders: function setGlobalHeaders() {},
  setGlobalTheme: function setGlobalTheme() {},
  setGlobalConfig: function setGlobalConfig() {}
};

// 创建上下文
var LLMManagerContext = /*#__PURE__*/createContext(defaultContext);

/**
 * LLM Manager 上下文提供者
 * 
 * @param {Object} props - 组件属性
 * @param {Object} props.headers - 全局请求头
 * @param {Object} props.theme - 全局主题配置
 * @param {Object} props.config - 全局配置
 * @param {ReactNode} props.children - 子组件
 */
export var LLMManagerProvider = function LLMManagerProvider(_ref) {
  var _ref$headers = _ref.headers,
    headers = _ref$headers === void 0 ? {} : _ref$headers,
    _ref$theme = _ref.theme,
    theme = _ref$theme === void 0 ? {} : _ref$theme,
    _ref$config = _ref.config,
    config = _ref$config === void 0 ? {} : _ref$config,
    children = _ref.children;
  // 状态管理
  var _useState = useState(headers),
    _useState2 = _slicedToArray(_useState, 2),
    globalHeaders = _useState2[0],
    setGlobalHeaders = _useState2[1];
  var _useState3 = useState(_objectSpread(_objectSpread({}, defaultContext.globalTheme), theme)),
    _useState4 = _slicedToArray(_useState3, 2),
    globalTheme = _useState4[0],
    setGlobalTheme = _useState4[1];
  var _useState5 = useState(_objectSpread(_objectSpread({}, defaultContext.globalConfig), config)),
    _useState6 = _slicedToArray(_useState5, 2),
    globalConfig = _useState6[0],
    setGlobalConfig = _useState6[1];

  // 监听配置变化
  useEffect(function () {
    setGlobalHeaders(_objectSpread(_objectSpread({}, globalHeaders), headers));
  }, [headers]);
  useEffect(function () {
    setGlobalTheme(_objectSpread(_objectSpread({}, globalTheme), theme));
  }, [theme]);
  useEffect(function () {
    setGlobalConfig(_objectSpread(_objectSpread({}, globalConfig), config));
  }, [config]);

  // 上下文值
  var contextValue = {
    globalHeaders: globalHeaders,
    globalTheme: globalTheme,
    globalConfig: globalConfig,
    setGlobalHeaders: setGlobalHeaders,
    setGlobalTheme: setGlobalTheme,
    setGlobalConfig: setGlobalConfig
  };
  return /*#__PURE__*/React.createElement(LLMManagerContext.Provider, {
    value: contextValue
  }, children);
};

/**
 * 使用LLM Manager上下文的钩子
 * 
 * @returns {Object} 上下文值
 */
export var useLLMManager = function useLLMManager() {
  var context = useContext(LLMManagerContext);
  if (!context) {
    throw new Error('useLLMManager must be used within a LLMManagerProvider');
  }
  return context;
};
export { LLMManagerContext as default };