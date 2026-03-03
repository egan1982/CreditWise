function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _regenerator() { /*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE */ var e, t, r = "function" == typeof Symbol ? Symbol : {}, n = r.iterator || "@@iterator", o = r.toStringTag || "@@toStringTag"; function i(r, n, o, i) { var c = n && n.prototype instanceof Generator ? n : Generator, u = Object.create(c.prototype); return _regeneratorDefine2(u, "_invoke", function (r, n, o) { var i, c, u, f = 0, p = o || [], y = !1, G = { p: 0, n: 0, v: e, a: d, f: d.bind(e, 4), d: function d(t, r) { return i = t, c = 0, u = e, G.n = r, a; } }; function d(r, n) { for (c = r, u = n, t = 0; !y && f && !o && t < p.length; t++) { var o, i = p[t], d = G.p, l = i[2]; r > 3 ? (o = l === n) && (u = i[(c = i[4]) ? 5 : (c = 3, 3)], i[4] = i[5] = e) : i[0] <= d && ((o = r < 2 && d < i[1]) ? (c = 0, G.v = n, G.n = i[1]) : d < l && (o = r < 3 || i[0] > n || n > l) && (i[4] = r, i[5] = n, G.n = l, c = 0)); } if (o || r > 1) return a; throw y = !0, n; } return function (o, p, l) { if (f > 1) throw TypeError("Generator is already running"); for (y && 1 === p && d(p, l), c = p, u = l; (t = c < 2 ? e : u) || !y;) { i || (c ? c < 3 ? (c > 1 && (G.n = -1), d(c, u)) : G.n = u : G.v = u); try { if (f = 2, i) { if (c || (o = "next"), t = i[o]) { if (!(t = t.call(i, u))) throw TypeError("iterator result is not an object"); if (!t.done) return t; u = t.value, c < 2 && (c = 0); } else 1 === c && (t = i["return"]) && t.call(i), c < 2 && (u = TypeError("The iterator does not provide a '" + o + "' method"), c = 1); i = e; } else if ((t = (y = G.n < 0) ? u : r.call(n, G)) !== a) break; } catch (t) { i = e, c = 1, u = t; } finally { f = 1; } } return { value: t, done: y }; }; }(r, o, i), !0), u; } var a = {}; function Generator() {} function GeneratorFunction() {} function GeneratorFunctionPrototype() {} t = Object.getPrototypeOf; var c = [][n] ? t(t([][n]())) : (_regeneratorDefine2(t = {}, n, function () { return this; }), t), u = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(c); function f(e) { return Object.setPrototypeOf ? Object.setPrototypeOf(e, GeneratorFunctionPrototype) : (e.__proto__ = GeneratorFunctionPrototype, _regeneratorDefine2(e, o, "GeneratorFunction")), e.prototype = Object.create(u), e; } return GeneratorFunction.prototype = GeneratorFunctionPrototype, _regeneratorDefine2(u, "constructor", GeneratorFunctionPrototype), _regeneratorDefine2(GeneratorFunctionPrototype, "constructor", GeneratorFunction), GeneratorFunction.displayName = "GeneratorFunction", _regeneratorDefine2(GeneratorFunctionPrototype, o, "GeneratorFunction"), _regeneratorDefine2(u), _regeneratorDefine2(u, o, "Generator"), _regeneratorDefine2(u, n, function () { return this; }), _regeneratorDefine2(u, "toString", function () { return "[object Generator]"; }), (_regenerator = function _regenerator() { return { w: i, m: f }; })(); }
function _regeneratorDefine2(e, r, n, t) { var i = Object.defineProperty; try { i({}, "", {}); } catch (e) { i = 0; } _regeneratorDefine2 = function _regeneratorDefine(e, r, n, t) { function o(r, n) { _regeneratorDefine2(e, r, function (e) { return this._invoke(r, n, e); }); } r ? i ? i(e, r, { value: n, enumerable: !t, configurable: !t, writable: !t }) : e[r] = n : (o("next", 0), o("throw", 1), o("return", 2)); }, _regeneratorDefine2(e, r, n, t); }
function asyncGeneratorStep(n, t, e, r, o, a, c) { try { var i = n[a](c), u = i.value; } catch (n) { return void e(n); } i.done ? t(u) : Promise.resolve(u).then(r, o); }
function _asyncToGenerator(n) { return function () { var t = this, e = arguments; return new Promise(function (r, o) { var a = n.apply(t, e); function _next(n) { asyncGeneratorStep(a, r, o, _next, _throw, "next", n); } function _throw(n) { asyncGeneratorStep(a, r, o, _next, _throw, "throw", n); } _next(void 0); }); }; }
function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
/**
 * LLM API Manager - ChannelManager 组件
 * 
 * 可集成到任何React应用的渠道管理组件
 * 
 * @version 1.0.0
 */

import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import { LLMManagerContext } from './contexts/LLMManagerContext';
import apiClient from './utils/api';

/**
 * ChannelManager 组件
 * 
 * @param {Object} props - 组件属性
 * @param {string} props.apiEndpoint - API端点
 * @param {Object} props.headers - 请求头
 * @param {Function} props.onChannelSelect - 渠道选择回调
 * @param {boolean} props.showActions - 是否显示操作按钮
 * @param {Object} props.customStyles - 自定义样式
 * @param {Object} props.theme - 主题配置
 * @param {boolean} props.selectable - 是否可选择渠道
 * @param {Function} props.onApiError - API错误回调
 */
var ChannelManager = function ChannelManager(_ref) {
  var _ref$apiEndpoint = _ref.apiEndpoint,
    apiEndpoint = _ref$apiEndpoint === void 0 ? '/api/manage/channels' : _ref$apiEndpoint,
    _ref$headers = _ref.headers,
    headers = _ref$headers === void 0 ? {} : _ref$headers,
    onChannelSelect = _ref.onChannelSelect,
    _ref$showActions = _ref.showActions,
    showActions = _ref$showActions === void 0 ? true : _ref$showActions,
    _ref$customStyles = _ref.customStyles,
    customStyles = _ref$customStyles === void 0 ? {} : _ref$customStyles,
    _ref$theme = _ref.theme,
    theme = _ref$theme === void 0 ? {} : _ref$theme,
    _ref$selectable = _ref.selectable,
    selectable = _ref$selectable === void 0 ? false : _ref$selectable,
    onApiError = _ref.onApiError;
  // 从上下文获取全局配置
  var _useContext = useContext(LLMManagerContext),
    globalHeaders = _useContext.globalHeaders,
    globalTheme = _useContext.globalTheme;

  // 合并全局配置
  var mergedHeaders = _objectSpread(_objectSpread({}, globalHeaders), headers);
  var mergedTheme = _objectSpread(_objectSpread({}, globalTheme), theme);

  // 组件状态
  var _useState = useState([]),
    _useState2 = _slicedToArray(_useState, 2),
    channels = _useState2[0],
    setChannels = _useState2[1];
  var _useState3 = useState(true),
    _useState4 = _slicedToArray(_useState3, 2),
    loading = _useState4[0],
    setLoading = _useState4[1];
  var _useState5 = useState(null),
    _useState6 = _slicedToArray(_useState5, 2),
    error = _useState6[0],
    setError = _useState6[1];
  var _useState7 = useState(null),
    _useState8 = _slicedToArray(_useState7, 2),
    selectedChannel = _useState8[0],
    setSelectedChannel = _useState8[1];

  // 默认样式
  var defaultStyles = {
    container: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
      color: mergedTheme.textColor || '#333'
    },
    toolbar: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '20px',
      alignItems: 'center'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse',
      marginTop: '20px',
      backgroundColor: '#fff'
    },
    th: {
      backgroundColor: mergedTheme.headerBgColor || '#f2f2f2',
      padding: '12px 15px',
      textAlign: 'left',
      borderBottom: '1px solid #ddd',
      fontWeight: 'bold'
    },
    td: {
      padding: '12px 15px',
      borderBottom: '1px solid #ddd'
    },
    enabledRow: {
      backgroundColor: 'rgba(46, 204, 113, 0.1)',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05) inset'
    },
    button: {
      padding: '6px 12px',
      margin: '0 5px',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
      fontWeight: '500'
    },
    primaryButton: {
      backgroundColor: mergedTheme.primaryColor || '#3498db',
      color: '#fff'
    },
    successButton: {
      backgroundColor: mergedTheme.successColor || '#2ecc71',
      color: '#fff'
    },
    dangerButton: {
      backgroundColor: mergedTheme.dangerColor || '#e74c3c',
      color: '#fff'
    },
    secondaryButton: {
      backgroundColor: mergedTheme.secondaryColor || '#95a5a6',
      color: '#fff'
    }
  };

  // 合并自定义样式
  var styles = _objectSpread(_objectSpread({}, defaultStyles), customStyles);

  // 获取渠道数据
  useEffect(function () {
    fetchChannels();
  }, [apiEndpoint, mergedHeaders]);
  var fetchChannels = /*#__PURE__*/function () {
    var _ref2 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee() {
      var response, _response$data, _response$data2, errorMsg, _t;
      return _regenerator().w(function (_context) {
        while (1) switch (_context.p = _context.n) {
          case 0:
            _context.p = 0;
            setLoading(true);
            setError(null);
            _context.n = 1;
            return apiClient.get(apiEndpoint, {
              headers: mergedHeaders
            });
          case 1:
            response = _context.v;
            if (response.data && response.data.status === 'success') {
              setChannels(response.data.data || []);
            } else {
              setError(((_response$data = response.data) === null || _response$data === void 0 ? void 0 : _response$data.message) || '获取渠道失败');
              if (onApiError) {
                onApiError(new Error(((_response$data2 = response.data) === null || _response$data2 === void 0 ? void 0 : _response$data2.message) || '获取渠道失败'));
              }
            }
            _context.n = 3;
            break;
          case 2:
            _context.p = 2;
            _t = _context.v;
            errorMsg = '网络请求失败';
            setError(errorMsg);
            if (onApiError) {
              onApiError(_t);
            }
          case 3:
            _context.p = 3;
            setLoading(false);
            return _context.f(3);
          case 4:
            return _context.a(2);
        }
      }, _callee, null, [[0, 2, 3, 4]]);
    }));
    return function fetchChannels() {
      return _ref2.apply(this, arguments);
    };
  }();
  var handleChannelClick = function handleChannelClick(channel) {
    setSelectedChannel(channel);
    if (onChannelSelect) {
      onChannelSelect(channel);
    }
  };
  var handleTest = /*#__PURE__*/function () {
    var _ref3 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee2(channelId) {
      var response, _response$data3, _t2;
      return _regenerator().w(function (_context2) {
        while (1) switch (_context2.p = _context2.n) {
          case 0:
            _context2.p = 0;
            _context2.n = 1;
            return apiClient.post("".concat(apiEndpoint, "/").concat(channelId, "/test"), null, {
              headers: mergedHeaders
            });
          case 1:
            response = _context2.v;
            if (response.data && response.data.status === 'success') {
              alert('渠道测试成功');
            } else {
              alert("\u6E20\u9053\u6D4B\u8BD5\u5931\u8D25: ".concat(((_response$data3 = response.data) === null || _response$data3 === void 0 ? void 0 : _response$data3.message) || '未知错误'));
            }
            _context2.n = 3;
            break;
          case 2:
            _context2.p = 2;
            _t2 = _context2.v;
            alert('测试请求失败');
          case 3:
            return _context2.a(2);
        }
      }, _callee2, null, [[0, 2]]);
    }));
    return function handleTest(_x) {
      return _ref3.apply(this, arguments);
    };
  }();
  var handleToggleStatus = /*#__PURE__*/function () {
    var _ref4 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee3(channelId, currentStatus) {
      var channel, channelName, action, response, _response$data4, _t3;
      return _regenerator().w(function (_context3) {
        while (1) switch (_context3.p = _context3.n) {
          case 0:
            channel = channels.find(function (ch) {
              return ch.id === channelId;
            });
            channelName = channel ? channel.name : '此渠道'; // 显示确认对话框
            action = currentStatus ? '禁用' : '启用';
            if (window.confirm("\u786E\u5B9A\u8981".concat(action, " \"").concat(channelName, "\" \u5417\uFF1F"))) {
              _context3.n = 1;
              break;
            }
            return _context3.a(2);
          case 1:
            _context3.p = 1;
            _context3.n = 2;
            return apiClient.put("".concat(apiEndpoint, "/").concat(channelId), {
              status: !currentStatus
            }, {
              headers: mergedHeaders
            });
          case 2:
            response = _context3.v;
            if (response.data && response.data.status === 'success') {
              // 只更新当前渠道状态，不影响其他渠道（支持多配置并存）
              setChannels(channels.map(function (ch) {
                return ch.id === channelId ? _objectSpread(_objectSpread({}, ch), {}, {
                  status: !currentStatus
                }) : ch;
              }));
            } else {
              alert("\u72B6\u6001\u66F4\u65B0\u5931\u8D25: ".concat(((_response$data4 = response.data) === null || _response$data4 === void 0 ? void 0 : _response$data4.message) || '未知错误'));
            }
            _context3.n = 4;
            break;
          case 3:
            _context3.p = 3;
            _t3 = _context3.v;
            alert('状态更新请求失败');
          case 4:
            return _context3.a(2);
        }
      }, _callee3, null, [[1, 3]]);
    }));
    return function handleToggleStatus(_x2, _x3) {
      return _ref4.apply(this, arguments);
    };
  }();
  var handleDelete = /*#__PURE__*/function () {
    var _ref5 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee4(channelId) {
      var response, _response$data5, _t4;
      return _regenerator().w(function (_context4) {
        while (1) switch (_context4.p = _context4.n) {
          case 0:
            if (window.confirm('确定要删除此渠道吗？')) {
              _context4.n = 1;
              break;
            }
            return _context4.a(2);
          case 1:
            _context4.p = 1;
            _context4.n = 2;
            return apiClient["delete"]("".concat(apiEndpoint, "/").concat(channelId), {
              headers: mergedHeaders
            });
          case 2:
            response = _context4.v;
            if (response.data && response.data.status === 'success') {
              // 从本地状态中移除
              setChannels(channels.filter(function (ch) {
                return ch.id !== channelId;
              }));
            } else {
              alert("\u5220\u9664\u5931\u8D25: ".concat(((_response$data5 = response.data) === null || _response$data5 === void 0 ? void 0 : _response$data5.message) || '未知错误'));
            }
            _context4.n = 4;
            break;
          case 3:
            _context4.p = 3;
            _t4 = _context4.v;
            alert('删除请求失败');
          case 4:
            return _context4.a(2);
        }
      }, _callee4, null, [[1, 3]]);
    }));
    return function handleDelete(_x4) {
      return _ref5.apply(this, arguments);
    };
  }();

  // 渲染加载状态
  if (loading) {
    return /*#__PURE__*/React.createElement("div", {
      style: styles.container
    }, /*#__PURE__*/React.createElement("div", null, "\u52A0\u8F7D\u4E2D..."));
  }

  // 渲染错误状态
  if (error) {
    return /*#__PURE__*/React.createElement("div", {
      style: styles.container
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        color: mergedTheme.dangerColor || '#e74c3c'
      }
    }, "\u9519\u8BEF: ", error));
  }

  // 渲染渠道管理界面
  return /*#__PURE__*/React.createElement("div", {
    style: styles.container
  }, /*#__PURE__*/React.createElement("h2", null, "\u6E20\u9053\u7BA1\u7406"), /*#__PURE__*/React.createElement("div", {
    style: {
      backgroundColor: mergedTheme.infoBgColor || '#e3f2fd',
      borderLeft: "4px solid ".concat(mergedTheme.infoColor || '#2196f3'),
      padding: '10px 15px',
      marginBottom: '15px',
      borderRadius: '4px',
      fontSize: '14px'
    }
  }, /*#__PURE__*/React.createElement("strong", null, "\u63D0\u793A\uFF1A"), "\u7CFB\u7EDF\u652F\u6301\u591A\u914D\u7F6E\u5E76\u5B58\uFF0C\u53EF\u540C\u65F6\u542F\u7528\u591A\u4E2A\u6E20\u9053\u914D\u7F6E\u3002\u5728AI\u5BF9\u8BDD\u65F6\u53EF\u6839\u636E\u4EFB\u52A1\u7C7B\u578B\u9009\u62E9\u5408\u9002\u7684\u914D\u7F6E\u3002"), /*#__PURE__*/React.createElement("div", {
    style: styles.toolbar
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", null, "\u5171 ", channels.length, " \u4E2A\u6E20\u9053"), channels.some(function (ch) {
    return ch.status;
  }) && /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: '10px',
      color: mergedTheme.successColor || '#2ecc71',
      fontWeight: 'bold'
    }
  }, "(", channels.filter(function (ch) {
    return ch.status;
  }).length, " \u4E2A\u5DF2\u542F\u7528)")), showActions && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("button", {
    style: _objectSpread(_objectSpread({}, styles.button), styles.primaryButton),
    onClick: function onClick() {
      return alert('新建渠道功能待实现');
    }
  }, "\u65B0\u5EFA\u6E20\u9053"))), /*#__PURE__*/React.createElement("table", {
    style: styles.table
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "ID"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u540D\u79F0"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u7C7B\u578B"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u6A21\u578B"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u72B6\u6001"), showActions && /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u64CD\u4F5C"))), /*#__PURE__*/React.createElement("tbody", null, channels.map(function (channel) {
    return /*#__PURE__*/React.createElement("tr", {
      key: channel.id,
      onClick: function onClick() {
        return selectable && handleChannelClick(channel);
      },
      style: _objectSpread(_objectSpread({
        cursor: selectable ? 'pointer' : 'default',
        backgroundColor: selectable && (selectedChannel === null || selectedChannel === void 0 ? void 0 : selectedChannel.id) === channel.id ? mergedTheme.selectedBgColor || '#e3f2fd' : 'transparent'
      }, channel.status && !selectable ? styles.enabledRow : {}), channel.status && selectable && (selectedChannel === null || selectedChannel === void 0 ? void 0 : selectedChannel.id) !== channel.id ? styles.enabledRow : {})
    }, /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, channel.id), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, channel.name), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, channel.type), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, channel.models, channel.supports_web_search && /*#__PURE__*/React.createElement("span", {
      title: "\u652F\u6301\u8054\u7F51\u641C\u7D22"
    }, " \uD83C\uDF10"), channel.supports_deep_thinking && /*#__PURE__*/React.createElement("span", {
      title: "\u652F\u6301\u6DF1\u5EA6\u63A8\u7406"
    }, " \uD83E\uDDE0")), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, showActions ? /*#__PURE__*/React.createElement("button", {
      style: _objectSpread(_objectSpread(_objectSpread({}, styles.button), channel.status ? styles.successButton : styles.secondaryButton), {}, {
        position: 'relative',
        paddingRight: channel.status ? '25px' : '12px'
      }),
      onClick: function onClick(e) {
        e.stopPropagation();
        handleToggleStatus(channel.id, channel.status);
      },
      title: channel.status ? '点击禁用此渠道' : '点击启用此渠道'
    }, channel.status ? '已启用' : '已禁用', channel.status && /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        right: '5px',
        top: '50%',
        transform: 'translateY(-50%)',
        fontSize: '12px'
      }
    }, "\u2713")) : /*#__PURE__*/React.createElement("span", {
      style: {
        color: channel.status ? mergedTheme.successColor || '#2ecc71' : mergedTheme.secondaryColor || '#95a5a6',
        fontWeight: 'bold'
      }
    }, channel.status ? '✓ 已启用' : '○ 已禁用')), showActions && /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, /*#__PURE__*/React.createElement("button", {
      style: _objectSpread(_objectSpread({}, styles.button), styles.secondaryButton),
      onClick: function onClick(e) {
        e.stopPropagation();
        handleTest(channel.id);
      }
    }, "\u6D4B\u8BD5"), /*#__PURE__*/React.createElement("button", {
      style: _objectSpread(_objectSpread({}, styles.button), styles.primaryButton),
      onClick: function onClick(e) {
        e.stopPropagation();
        alert('编辑功能待实现');
      }
    }, "\u7F16\u8F91"), /*#__PURE__*/React.createElement("button", {
      style: _objectSpread(_objectSpread({}, styles.button), styles.dangerButton),
      onClick: function onClick(e) {
        e.stopPropagation();
        handleDelete(channel.id);
      }
    }, "\u5220\u9664")));
  }))));
};
ChannelManager.propTypes = {
  apiEndpoint: PropTypes.string,
  headers: PropTypes.object,
  onChannelSelect: PropTypes.func,
  showActions: PropTypes.bool,
  customStyles: PropTypes.object,
  theme: PropTypes.object,
  selectable: PropTypes.bool,
  onApiError: PropTypes.func
};
export default ChannelManager;