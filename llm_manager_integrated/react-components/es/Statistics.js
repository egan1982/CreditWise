function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _toConsumableArray(r) { return _arrayWithoutHoles(r) || _iterableToArray(r) || _unsupportedIterableToArray(r) || _nonIterableSpread(); }
function _nonIterableSpread() { throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _iterableToArray(r) { if ("undefined" != typeof Symbol && null != r[Symbol.iterator] || null != r["@@iterator"]) return Array.from(r); }
function _arrayWithoutHoles(r) { if (Array.isArray(r)) return _arrayLikeToArray(r); }
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
 * LLM API Manager - Statistics 组件
 * 
 * 可集成到任何React应用的统计分析组件
 * 
 * @version 1.0.0
 */

import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import { LLMManagerContext } from './contexts/LLMManagerContext';
import apiClient from './utils/api';

/**
 * Statistics 组件
 * 
 * @param {Object} props - 组件属性
 * @param {string} props.apiEndpoint - API端点
 * @param {Object} props.headers - 请求头
 * @param {Object} props.customStyles - 自定义样式
 * @param {Object} props.theme - 主题配置
 * @param {Function} props.onApiError - API错误回调
 * @param {boolean} props.showFilters - 是否显示过滤器
 */
var Statistics = function Statistics(_ref) {
  var _ref$apiEndpoint = _ref.apiEndpoint,
    apiEndpoint = _ref$apiEndpoint === void 0 ? '/api/logs/stats' : _ref$apiEndpoint,
    _ref$headers = _ref.headers,
    headers = _ref$headers === void 0 ? {} : _ref$headers,
    _ref$customStyles = _ref.customStyles,
    customStyles = _ref$customStyles === void 0 ? {} : _ref$customStyles,
    _ref$theme = _ref.theme,
    theme = _ref$theme === void 0 ? {} : _ref$theme,
    _ref$showFilters = _ref.showFilters,
    showFilters = _ref$showFilters === void 0 ? true : _ref$showFilters,
    onApiError = _ref.onApiError;
  // 从上下文获取全局配置
  var _useContext = useContext(LLMManagerContext),
    globalHeaders = _useContext.globalHeaders,
    globalTheme = _useContext.globalTheme;

  // 合并全局配置
  var mergedHeaders = _objectSpread(_objectSpread({}, globalHeaders), headers);
  var mergedTheme = _objectSpread(_objectSpread({}, globalTheme), theme);

  // 组件状态
  var _useState = useState(null),
    _useState2 = _slicedToArray(_useState, 2),
    stats = _useState2[0],
    setStats = _useState2[1];
  var _useState3 = useState([]),
    _useState4 = _slicedToArray(_useState3, 2),
    logs = _useState4[0],
    setLogs = _useState4[1];
  var _useState5 = useState(true),
    _useState6 = _slicedToArray(_useState5, 2),
    loading = _useState6[0],
    setLoading = _useState6[1];
  var _useState7 = useState(null),
    _useState8 = _slicedToArray(_useState7, 2),
    error = _useState8[0],
    setError = _useState8[1];
  var _useState9 = useState('7'),
    _useState0 = _slicedToArray(_useState9, 2),
    timeRange = _useState0[0],
    setTimeRange = _useState0[1]; // 默认7天
  var _useState1 = useState('calls'),
    _useState10 = _slicedToArray(_useState1, 2),
    chartType = _useState10[0],
    setChartType = _useState10[1]; // calls, cost, tokens
  var _useState11 = useState(false),
    _useState12 = _slicedToArray(_useState11, 2),
    excludeTestData = _useState12[0],
    setExcludeTestData = _useState12[1];

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
    filterSelect: {
      padding: '8px 12px',
      border: "1px solid ".concat(mergedTheme.borderColor || '#ddd'),
      borderRadius: '4px',
      backgroundColor: '#fff'
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
    statsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
      gap: '15px',
      marginBottom: '30px'
    },
    statCard: {
      backgroundColor: mergedTheme.cardBgColor || '#f8f9fa',
      padding: '15px',
      borderRadius: '8px',
      border: "1px solid ".concat(mergedTheme.borderColor || '#eee')
    },
    statTitle: {
      fontSize: '14px',
      color: mergedTheme.secondaryTextColor || '#666',
      marginBottom: '8px'
    },
    statValue: {
      fontSize: '24px',
      fontWeight: 'bold',
      color: mergedTheme.primaryColor || '#3498db'
    },
    chartContainer: {
      backgroundColor: mergedTheme.cardBgColor || '#f8f9fa',
      padding: '20px',
      borderRadius: '8px',
      border: "1px solid ".concat(mergedTheme.borderColor || '#eee')
    }
  };

  // 合并自定义样式
  var styles = _objectSpread(_objectSpread({}, defaultStyles), customStyles);

  // 获取统计数据
  useEffect(function () {
    fetchData();
  }, [apiEndpoint, mergedHeaders, timeRange, excludeTestData]);
  var fetchData = /*#__PURE__*/function () {
    var _ref2 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee() {
      var _yield$Promise$all, _yield$Promise$all2, statsResponse, logsResponse, errorMsg, _t;
      return _regenerator().w(function (_context) {
        while (1) switch (_context.p = _context.n) {
          case 0:
            _context.p = 0;
            setLoading(true);
            setError(null);
            _context.n = 1;
            return Promise.all([apiClient.get(apiEndpoint, {
              params: {
                time_range: timeRange,
                exclude_test_data: excludeTestData
              },
              headers: mergedHeaders
            }), apiClient.get('/api/logs', {
              params: {
                limit: 1000,
                time_range: timeRange,
                exclude_test_data: excludeTestData
              },
              headers: mergedHeaders
            })]);
          case 1:
            _yield$Promise$all = _context.v;
            _yield$Promise$all2 = _slicedToArray(_yield$Promise$all, 2);
            statsResponse = _yield$Promise$all2[0];
            logsResponse = _yield$Promise$all2[1];
            if (statsResponse.data && statsResponse.data.status === 'success') {
              setStats(statsResponse.data.data || {});
            }
            if (logsResponse.data && logsResponse.data.status === 'success') {
              setLogs(logsResponse.data.data || []);
            }
            _context.n = 3;
            break;
          case 2:
            _context.p = 2;
            _t = _context.v;
            errorMsg = '获取统计数据失败';
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
    return function fetchData() {
      return _ref2.apply(this, arguments);
    };
  }();
  var handleDeleteTestData = /*#__PURE__*/function () {
    var _ref3 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee2() {
      var response, _response$data, _t2;
      return _regenerator().w(function (_context2) {
        while (1) switch (_context2.p = _context2.n) {
          case 0:
            if (window.confirm('确定要删除所有测试数据吗？此操作不可撤销。')) {
              _context2.n = 1;
              break;
            }
            return _context2.a(2);
          case 1:
            _context2.p = 1;
            _context2.n = 2;
            return apiClient["delete"]('/api/logs/test-data', {
              headers: mergedHeaders
            });
          case 2:
            response = _context2.v;
            if (response.data && response.data.status === 'success') {
              alert(response.data.message || '测试数据删除成功');
              fetchData(); // 重新获取数据
            } else {
              alert("\u5220\u9664\u5931\u8D25: ".concat(((_response$data = response.data) === null || _response$data === void 0 ? void 0 : _response$data.message) || '未知错误'));
            }
            _context2.n = 4;
            break;
          case 3:
            _context2.p = 3;
            _t2 = _context2.v;
            alert('删除请求失败');
          case 4:
            return _context2.a(2);
        }
      }, _callee2, null, [[1, 3]]);
    }));
    return function handleDeleteTestData() {
      return _ref3.apply(this, arguments);
    };
  }();

  // 处理图表数据
  var processChartData = function processChartData() {
    if (!logs.length) return [];

    // 按日期分组
    var groupedByDate = {};
    logs.forEach(function (log) {
      var date = new Date(log.created_at).toLocaleDateString();
      if (!groupedByDate[date]) {
        groupedByDate[date] = {
          date: date,
          calls: 0,
          success: 0,
          error: 0,
          tokens: 0,
          cost: 0
        };
      }
      groupedByDate[date].calls += 1;
      if (log.status === 'success') {
        groupedByDate[date].success += 1;
      } else {
        groupedByDate[date].error += 1;
      }

      // 如果日志中有token和cost信息
      groupedByDate[date].tokens += log.tokens || 0;
      groupedByDate[date].cost += log.cost || 0;
    });

    // 转换为数组并排序
    return Object.values(groupedByDate).sort(function (a, b) {
      return new Date(a.date) - new Date(b.date);
    });
  };

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
  var chartData = processChartData();

  // 渲染统计界面
  return /*#__PURE__*/React.createElement("div", {
    style: styles.container
  }, /*#__PURE__*/React.createElement("h2", null, "\u7EDF\u8BA1\u5206\u6790"), /*#__PURE__*/React.createElement("div", {
    style: styles.toolbar
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", null, "API\u8C03\u7528\u7EDF\u8BA1"))), showFilters && /*#__PURE__*/React.createElement("div", {
    style: styles.filterContainer
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", null, "\u65F6\u95F4\u8303\u56F4: "), /*#__PURE__*/React.createElement("select", {
    style: styles.filterSelect,
    value: timeRange,
    onChange: function onChange(e) {
      return setTimeRange(e.target.value);
    }
  }, /*#__PURE__*/React.createElement("option", {
    value: "7"
  }, "\u6700\u8FD17\u5929"), /*#__PURE__*/React.createElement("option", {
    value: "30"
  }, "\u6700\u8FD130\u5929"), /*#__PURE__*/React.createElement("option", {
    value: "90"
  }, "\u6700\u8FD190\u5929"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", null, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: excludeTestData,
    onChange: function onChange(e) {
      return setExcludeTestData(e.target.checked);
    }
  }), "\u6392\u9664\u6D4B\u8BD5\u6570\u636E")), /*#__PURE__*/React.createElement("button", {
    style: _objectSpread(_objectSpread({}, styles.button), styles.dangerButton),
    onClick: handleDeleteTestData
  }, "\u5220\u9664\u6D4B\u8BD5\u6570\u636E")), /*#__PURE__*/React.createElement("div", {
    style: styles.statsGrid
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statCard
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statTitle
  }, "\u603B\u8C03\u7528\u6B21\u6570"), /*#__PURE__*/React.createElement("div", {
    style: styles.statValue
  }, (stats === null || stats === void 0 ? void 0 : stats.total_calls) || 0)), /*#__PURE__*/React.createElement("div", {
    style: styles.statCard
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statTitle
  }, "\u6210\u529F\u8C03\u7528"), /*#__PURE__*/React.createElement("div", {
    style: _objectSpread(_objectSpread({}, styles.statValue), {}, {
      color: mergedTheme.successColor || '#2ecc71'
    })
  }, (stats === null || stats === void 0 ? void 0 : stats.success_calls) || 0)), /*#__PURE__*/React.createElement("div", {
    style: styles.statCard
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statTitle
  }, "\u5931\u8D25\u8C03\u7528"), /*#__PURE__*/React.createElement("div", {
    style: _objectSpread(_objectSpread({}, styles.statValue), {}, {
      color: mergedTheme.dangerColor || '#e74c3c'
    })
  }, (stats === null || stats === void 0 ? void 0 : stats.error_calls) || 0)), /*#__PURE__*/React.createElement("div", {
    style: styles.statCard
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statTitle
  }, "\u6210\u529F\u7387"), /*#__PURE__*/React.createElement("div", {
    style: styles.statValue
  }, stats !== null && stats !== void 0 && stats.total_calls ? "".concat((stats.success_calls / stats.total_calls * 100).toFixed(1), "%") : '0%')), /*#__PURE__*/React.createElement("div", {
    style: styles.statCard
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statTitle
  }, "\u603BToken\u6570"), /*#__PURE__*/React.createElement("div", {
    style: styles.statValue
  }, (stats === null || stats === void 0 ? void 0 : stats.total_tokens) || 0)), /*#__PURE__*/React.createElement("div", {
    style: styles.statCard
  }, /*#__PURE__*/React.createElement("div", {
    style: styles.statTitle
  }, "\u603B\u82B1\u8D39"), /*#__PURE__*/React.createElement("div", {
    style: styles.statValue
  }, "$", (stats === null || stats === void 0 ? void 0 : stats.total_cost) || '0.00'))), /*#__PURE__*/React.createElement("div", {
    style: styles.chartContainer
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: '15px'
    }
  }, /*#__PURE__*/React.createElement("label", null, "\u56FE\u8868\u7C7B\u578B: "), /*#__PURE__*/React.createElement("select", {
    style: styles.filterSelect,
    value: chartType,
    onChange: function onChange(e) {
      return setChartType(e.target.value);
    }
  }, /*#__PURE__*/React.createElement("option", {
    value: "calls"
  }, "\u8C03\u7528\u6B21\u6570"), /*#__PURE__*/React.createElement("option", {
    value: "tokens"
  }, "Token\u4F7F\u7528\u91CF"), /*#__PURE__*/React.createElement("option", {
    value: "cost"
  }, "\u82B1\u8D39"))), /*#__PURE__*/React.createElement("div", {
    style: {
      height: '300px',
      position: 'relative'
    }
  }, chartData.length > 0 ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      height: '100%',
      gap: '10px'
    }
  }, chartData.map(function (item, index) {
    var value = 0;
    if (chartType === 'calls') value = item.calls;else if (chartType === 'tokens') value = item.tokens / 1000; // 转换为千tokens
    else if (chartType === 'cost') value = parseFloat(item.cost) * 100; // 放大显示

    var maxValue = Math.max.apply(Math, _toConsumableArray(chartData.map(function (d) {
      if (chartType === 'calls') return d.calls;else if (chartType === 'tokens') return d.tokens / 1000;else if (chartType === 'cost') return parseFloat(d.cost) * 100;
      return 0;
    })));
    var height = maxValue > 0 ? value / maxValue * 250 : 0;
    return /*#__PURE__*/React.createElement("div", {
      key: index,
      style: {
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        height: "".concat(height, "px"),
        width: '80%',
        backgroundColor: mergedTheme.primaryColor || '#3498db',
        borderRadius: '4px 4px 0 0',
        position: 'relative'
      },
      title: "".concat(item.date, ": ").concat(value)
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        top: '-20px',
        left: 0,
        right: 0,
        textAlign: 'center',
        fontSize: '12px'
      }
    }, value)), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: '5px',
        fontSize: '12px',
        textAlign: 'center'
      }
    }, new Date(item.date).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric'
    })));
  })) : /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100%',
      color: mergedTheme.secondaryTextColor || '#666'
    }
  }, "\u6682\u65E0\u6570\u636E"))));
};
Statistics.propTypes = {
  apiEndpoint: PropTypes.string,
  headers: PropTypes.object,
  customStyles: PropTypes.object,
  theme: PropTypes.object,
  showFilters: PropTypes.bool,
  onApiError: PropTypes.func
};
export default Statistics;