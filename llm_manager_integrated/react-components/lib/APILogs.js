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
 * LLM API Manager - APILogs 组件
 * 
 * 可集成到任何React应用的API日志组件
 * 
 * @version 1.0.0
 */

import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import { LLMManagerContext } from './contexts/LLMManagerContext';
import apiClient from './utils/api';

/**
 * APILogs 组件
 * 
 * @param {Object} props - 组件属性
 * @param {string} props.apiEndpoint - API端点
 * @param {Object} props.headers - 请求头
 * @param {Object} props.customStyles - 自定义样式
 * @param {Object} props.theme - 主题配置
 * @param {boolean} props.showFilters - 是否显示过滤器
 * @param {Function} props.onApiError - API错误回调
 * @param {number} props.pageSize - 每页显示数量
 */
var APILogs = function APILogs(_ref) {
  var _ref$apiEndpoint = _ref.apiEndpoint,
    apiEndpoint = _ref$apiEndpoint === void 0 ? '/api/logs' : _ref$apiEndpoint,
    _ref$headers = _ref.headers,
    headers = _ref$headers === void 0 ? {} : _ref$headers,
    _ref$customStyles = _ref.customStyles,
    customStyles = _ref$customStyles === void 0 ? {} : _ref$customStyles,
    _ref$theme = _ref.theme,
    theme = _ref$theme === void 0 ? {} : _ref$theme,
    _ref$showFilters = _ref.showFilters,
    showFilters = _ref$showFilters === void 0 ? true : _ref$showFilters,
    onApiError = _ref.onApiError,
    _ref$pageSize = _ref.pageSize,
    pageSize = _ref$pageSize === void 0 ? 20 : _ref$pageSize;
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
    logs = _useState2[0],
    setLogs = _useState2[1];
  var _useState3 = useState(null),
    _useState4 = _slicedToArray(_useState3, 2),
    stats = _useState4[0],
    setStats = _useState4[1];
  var _useState5 = useState(true),
    _useState6 = _slicedToArray(_useState5, 2),
    loading = _useState6[0],
    setLoading = _useState6[1];
  var _useState7 = useState(null),
    _useState8 = _slicedToArray(_useState7, 2),
    error = _useState8[0],
    setError = _useState8[1];
  var _useState9 = useState(1),
    _useState0 = _slicedToArray(_useState9, 2),
    currentPage = _useState0[0],
    setCurrentPage = _useState0[1];
  var _useState1 = useState(0),
    _useState10 = _slicedToArray(_useState1, 2),
    totalLogs = _useState10[0],
    setTotalLogs = _useState10[1];
  var _useState11 = useState(''),
    _useState12 = _slicedToArray(_useState11, 2),
    filterModel = _useState12[0],
    setFilterModel = _useState12[1];
  var _useState13 = useState(''),
    _useState14 = _slicedToArray(_useState13, 2),
    filterStatus = _useState14[0],
    setFilterStatus = _useState14[1];
  var _useState15 = useState(null),
    _useState16 = _slicedToArray(_useState15, 2),
    expandedLog = _useState16[0],
    setExpandedLog = _useState16[1];

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
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '10px'
    },
    filterContainer: {
      display: 'flex',
      gap: '10px',
      alignItems: 'center',
      marginBottom: '20px'
    },
    filterInput: {
      padding: '8px 12px',
      border: "1px solid ".concat(mergedTheme.borderColor || '#ddd'),
      borderRadius: '4px'
    },
    filterSelect: {
      padding: '8px 12px',
      border: "1px solid ".concat(mergedTheme.borderColor || '#ddd'),
      borderRadius: '4px',
      backgroundColor: '#fff'
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
      borderBottom: '1px solid #ddd',
      wordBreak: 'break-word'
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
    dangerButton: {
      backgroundColor: mergedTheme.dangerColor || '#e74c3c',
      color: '#fff'
    },
    pagination: {
      display: 'flex',
      justifyContent: 'center',
      marginTop: '20px',
      gap: '10px'
    },
    pageButton: {
      padding: '6px 12px',
      border: "1px solid ".concat(mergedTheme.borderColor || '#ddd'),
      borderRadius: '4px',
      cursor: 'pointer',
      backgroundColor: '#fff'
    },
    activePageButton: {
      backgroundColor: mergedTheme.primaryColor || '#3498db',
      color: '#fff',
      borderColor: mergedTheme.primaryColor || '#3498db'
    },
    logDetail: {
      backgroundColor: mergedTheme.detailBgColor || '#f8f9fa',
      padding: '15px',
      marginTop: '10px',
      borderRadius: '4px',
      borderLeft: "4px solid ".concat(mergedTheme.primaryColor || '#3498db')
    }
  };

  // 合并自定义样式
  var styles = _objectSpread(_objectSpread({}, defaultStyles), customStyles);

  // 获取日志数据
  useEffect(function () {
    fetchLogs();
    fetchStats();
  }, [apiEndpoint, mergedHeaders, currentPage, filterModel, filterStatus]);
  var fetchLogs = /*#__PURE__*/function () {
    var _ref2 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee() {
      var params, response, _response$data$data, _response$data, _response$data2, errorMsg, _t;
      return _regenerator().w(function (_context) {
        while (1) switch (_context.p = _context.n) {
          case 0:
            _context.p = 0;
            setLoading(true);
            setError(null);
            params = {
              skip: (currentPage - 1) * pageSize,
              limit: pageSize
            };
            if (filterModel) params.model_name = filterModel;
            if (filterStatus) params.status = filterStatus;
            _context.n = 1;
            return apiClient.get(apiEndpoint, {
              params: params,
              headers: mergedHeaders
            });
          case 1:
            response = _context.v;
            if (response.data && response.data.status === 'success') {
              setLogs(response.data.data || []);
              // 注意：实际API可能需要返回总数，这里假设总数等于当前返回的日志数
              setTotalLogs(((_response$data$data = response.data.data) === null || _response$data$data === void 0 ? void 0 : _response$data$data.length) || 0);
            } else {
              setError(((_response$data = response.data) === null || _response$data === void 0 ? void 0 : _response$data.message) || '获取日志失败');
              if (onApiError) {
                onApiError(new Error(((_response$data2 = response.data) === null || _response$data2 === void 0 ? void 0 : _response$data2.message) || '获取日志失败'));
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
    return function fetchLogs() {
      return _ref2.apply(this, arguments);
    };
  }();
  var fetchStats = /*#__PURE__*/function () {
    var _ref3 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee2() {
      var response, _t2;
      return _regenerator().w(function (_context2) {
        while (1) switch (_context2.p = _context2.n) {
          case 0:
            _context2.p = 0;
            _context2.n = 1;
            return apiClient.get("".concat(apiEndpoint, "/stats"), {
              headers: mergedHeaders
            });
          case 1:
            response = _context2.v;
            if (response.data && response.data.status === 'success') {
              setStats(response.data.data || {});
            }
            _context2.n = 3;
            break;
          case 2:
            _context2.p = 2;
            _t2 = _context2.v;
            console.error('获取统计信息失败:', _t2);
          case 3:
            return _context2.a(2);
        }
      }, _callee2, null, [[0, 2]]);
    }));
    return function fetchStats() {
      return _ref3.apply(this, arguments);
    };
  }();
  var handlePageChange = function handlePageChange(page) {
    setCurrentPage(page);
  };
  var handleClearLogs = /*#__PURE__*/function () {
    var _ref4 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee3() {
      var response, _response$data3, _t3;
      return _regenerator().w(function (_context3) {
        while (1) switch (_context3.p = _context3.n) {
          case 0:
            if (window.confirm('确定要清除30天前的日志吗？')) {
              _context3.n = 1;
              break;
            }
            return _context3.a(2);
          case 1:
            _context3.p = 1;
            _context3.n = 2;
            return apiClient["delete"]("".concat(apiEndpoint, "?days=30"), {
              headers: mergedHeaders
            });
          case 2:
            response = _context3.v;
            if (response.data && response.data.status === 'success') {
              alert(response.data.message || '日志清除成功');
              fetchLogs(); // 重新获取日志
              fetchStats(); // 重新获取统计
            } else {
              alert("\u6E05\u9664\u5931\u8D25: ".concat(((_response$data3 = response.data) === null || _response$data3 === void 0 ? void 0 : _response$data3.message) || '未知错误'));
            }
            _context3.n = 4;
            break;
          case 3:
            _context3.p = 3;
            _t3 = _context3.v;
            alert('清除请求失败');
          case 4:
            return _context3.a(2);
        }
      }, _callee3, null, [[1, 3]]);
    }));
    return function handleClearLogs() {
      return _ref4.apply(this, arguments);
    };
  }();
  var toggleLogDetail = function toggleLogDetail(logId) {
    setExpandedLog(expandedLog === logId ? null : logId);
  };

  // 渲染加载状态
  if (loading && logs.length === 0) {
    return /*#__PURE__*/React.createElement("div", {
      style: styles.container
    }, /*#__PURE__*/React.createElement("div", null, "\u52A0\u8F7D\u4E2D..."));
  }

  // 渲染错误状态
  if (error && logs.length === 0) {
    return /*#__PURE__*/React.createElement("div", {
      style: styles.container
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        color: mergedTheme.dangerColor || '#e74c3c'
      }
    }, "\u9519\u8BEF: ", error));
  }

  // 渲染日志界面
  return /*#__PURE__*/React.createElement("div", {
    style: styles.container
  }, /*#__PURE__*/React.createElement("h2", null, "API\u8C03\u7528\u65E5\u5FD7"), /*#__PURE__*/React.createElement("div", {
    style: styles.toolbar
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", null, "\u5171 ", totalLogs, " \u6761\u65E5\u5FD7"), stats && /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: '15px'
    }
  }, "\u4ECA\u65E5\u8C03\u7528: ", stats.today_calls || 0)), /*#__PURE__*/React.createElement("button", {
    style: _objectSpread(_objectSpread({}, styles.button), styles.dangerButton),
    onClick: handleClearLogs
  }, "\u6E05\u966430\u5929\u524D\u65E5\u5FD7")), showFilters && /*#__PURE__*/React.createElement("div", {
    style: styles.filterContainer
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", null, "\u6A21\u578B\u7B5B\u9009: "), /*#__PURE__*/React.createElement("input", {
    type: "text",
    style: styles.filterInput,
    value: filterModel,
    onChange: function onChange(e) {
      setFilterModel(e.target.value);
      setCurrentPage(1);
    },
    placeholder: "\u8F93\u5165\u6A21\u578B\u540D\u79F0"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", null, "\u72B6\u6001\u7B5B\u9009: "), /*#__PURE__*/React.createElement("select", {
    style: styles.filterSelect,
    value: filterStatus,
    onChange: function onChange(e) {
      setFilterStatus(e.target.value);
      setCurrentPage(1);
    }
  }, /*#__PURE__*/React.createElement("option", {
    value: ""
  }, "\u5168\u90E8"), /*#__PURE__*/React.createElement("option", {
    value: "success"
  }, "\u6210\u529F"), /*#__PURE__*/React.createElement("option", {
    value: "error"
  }, "\u5931\u8D25")))), /*#__PURE__*/React.createElement("table", {
    style: styles.table
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "ID"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u6A21\u578B"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u72B6\u6001"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u65F6\u95F4"), /*#__PURE__*/React.createElement("th", {
    style: styles.th
  }, "\u64CD\u4F5C"))), /*#__PURE__*/React.createElement("tbody", null, logs.map(function (log) {
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: log.id
    }, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, log.id), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, log.model_name), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: log.status === 'success' ? mergedTheme.successColor || '#2ecc71' : mergedTheme.dangerColor || '#e74c3c',
        fontWeight: 'bold'
      }
    }, log.status === 'success' ? '成功' : '失败')), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, new Date(log.created_at).toLocaleString()), /*#__PURE__*/React.createElement("td", {
      style: styles.td
    }, /*#__PURE__*/React.createElement("button", {
      style: _objectSpread(_objectSpread({}, styles.button), styles.primaryButton),
      onClick: function onClick() {
        return toggleLogDetail(log.id);
      }
    }, expandedLog === log.id ? '收起' : '详情'))), expandedLog === log.id && /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("td", {
      colSpan: "5",
      style: {
        padding: '0'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: styles.logDetail
    }, /*#__PURE__*/React.createElement("pre", {
      style: {
        margin: 0,
        whiteSpace: 'pre-wrap',
        fontSize: '14px',
        maxHeight: '200px',
        overflow: 'auto'
      }
    }, JSON.stringify(log, null, 2))))));
  }))), /*#__PURE__*/React.createElement("div", {
    style: styles.pagination
  }, /*#__PURE__*/React.createElement("button", {
    style: styles.pageButton,
    disabled: currentPage === 1,
    onClick: function onClick() {
      return handlePageChange(currentPage - 1);
    }
  }, "\u4E0A\u4E00\u9875"), /*#__PURE__*/React.createElement("span", {
    style: {
      margin: '0 10px'
    }
  }, "\u7B2C ", currentPage, " \u9875"), /*#__PURE__*/React.createElement("button", {
    style: styles.pageButton,
    disabled: logs.length < pageSize,
    onClick: function onClick() {
      return handlePageChange(currentPage + 1);
    }
  }, "\u4E0B\u4E00\u9875")));
};
APILogs.propTypes = {
  apiEndpoint: PropTypes.string,
  headers: PropTypes.object,
  customStyles: PropTypes.object,
  theme: PropTypes.object,
  showFilters: PropTypes.bool,
  onApiError: PropTypes.func,
  pageSize: PropTypes.number
};
export default APILogs;