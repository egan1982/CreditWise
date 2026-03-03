function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
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
/**
 * LLM Manager 钩子函数
 * 
 * 提供常用的状态管理和操作
 */

import { useState, useEffect, useCallback } from 'react';
import { useLLMManager } from '../contexts/LLMManagerContext';
import apiClient from '../utils/api';

/**
 * 使用API数据的钩子
 * 
 * @param {string} endpoint - API端点
 * @param {Object} options - 选项
 * @param {Object} options.params - 请求参数
 * @param {Array} options.deps - 依赖数组，变化时重新获取数据
 * @param {boolean} options.immediate - 是否立即获取数据
 * @param {Function} options.transform - 数据转换函数
 * @returns {Object} 状态和操作
 */
export var useApiData = function useApiData(endpoint) {
  var options = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  var _useLLMManager = useLLMManager(),
    globalHeaders = _useLLMManager.globalHeaders;
  var _options$params = options.params,
    params = _options$params === void 0 ? {} : _options$params,
    _options$deps = options.deps,
    deps = _options$deps === void 0 ? [] : _options$deps,
    _options$immediate = options.immediate,
    immediate = _options$immediate === void 0 ? true : _options$immediate,
    _options$transform = options.transform,
    transform = _options$transform === void 0 ? function (data) {
      return data;
    } : _options$transform;
  var _useState = useState(null),
    _useState2 = _slicedToArray(_useState, 2),
    data = _useState2[0],
    setData = _useState2[1];
  var _useState3 = useState(false),
    _useState4 = _slicedToArray(_useState3, 2),
    loading = _useState4[0],
    setLoading = _useState4[1];
  var _useState5 = useState(null),
    _useState6 = _slicedToArray(_useState5, 2),
    error = _useState6[0],
    setError = _useState6[1];
  var fetchData = useCallback(/*#__PURE__*/_asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee() {
    var response, _response$data, _t;
    return _regenerator().w(function (_context) {
      while (1) switch (_context.p = _context.n) {
        case 0:
          _context.p = 0;
          setLoading(true);
          setError(null);
          _context.n = 1;
          return apiClient.get(endpoint, {
            params: params,
            headers: globalHeaders
          });
        case 1:
          response = _context.v;
          if (response.data && response.data.status === 'success') {
            setData(transform(response.data.data));
          } else {
            setError(((_response$data = response.data) === null || _response$data === void 0 ? void 0 : _response$data.message) || '获取数据失败');
          }
          _context.n = 3;
          break;
        case 2:
          _context.p = 2;
          _t = _context.v;
          setError(_t.message || '网络请求失败');
        case 3:
          _context.p = 3;
          setLoading(false);
          return _context.f(3);
        case 4:
          return _context.a(2);
      }
    }, _callee, null, [[0, 2, 3, 4]]);
  })), [endpoint, globalHeaders, params, transform]);
  useEffect(function () {
    if (immediate) {
      fetchData();
    }
  }, [fetchData, immediate].concat(_toConsumableArray(deps)));
  var refetch = useCallback(function () {
    fetchData();
  }, [fetchData]);
  return {
    data: data,
    loading: loading,
    error: error,
    refetch: refetch
  };
};

/**
 * 使用API操作（POST/PUT/DELETE）的钩子
 * 
 * @returns {Object} 操作函数和状态
 */
export var useApiAction = function useApiAction() {
  var _useLLMManager2 = useLLMManager(),
    globalHeaders = _useLLMManager2.globalHeaders;
  var _useState7 = useState(false),
    _useState8 = _slicedToArray(_useState7, 2),
    loading = _useState8[0],
    setLoading = _useState8[1];
  var _useState9 = useState(null),
    _useState0 = _slicedToArray(_useState9, 2),
    error = _useState0[0],
    setError = _useState0[1];
  var execute = useCallback(/*#__PURE__*/function () {
    var _ref2 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee2(method, url) {
      var data,
        config,
        response,
        _args2 = arguments,
        _t2,
        _t3;
      return _regenerator().w(function (_context2) {
        while (1) switch (_context2.p = _context2.n) {
          case 0:
            data = _args2.length > 2 && _args2[2] !== undefined ? _args2[2] : null;
            _context2.p = 1;
            setLoading(true);
            setError(null);
            config = {
              headers: globalHeaders
            };
            _t2 = method.toLowerCase();
            _context2.n = _t2 === 'post' ? 2 : _t2 === 'put' ? 4 : _t2 === 'delete' ? 6 : 8;
            break;
          case 2:
            _context2.n = 3;
            return apiClient.post(url, data, config);
          case 3:
            response = _context2.v;
            return _context2.a(3, 9);
          case 4:
            _context2.n = 5;
            return apiClient.put(url, data, config);
          case 5:
            response = _context2.v;
            return _context2.a(3, 9);
          case 6:
            _context2.n = 7;
            return apiClient["delete"](url, config);
          case 7:
            response = _context2.v;
            return _context2.a(3, 9);
          case 8:
            throw new Error("\u4E0D\u652F\u6301\u7684HTTP\u65B9\u6CD5: ".concat(method));
          case 9:
            return _context2.a(2, response.data);
          case 10:
            _context2.p = 10;
            _t3 = _context2.v;
            setError(_t3.message || '操作失败');
            throw _t3;
          case 11:
            _context2.p = 11;
            setLoading(false);
            return _context2.f(11);
          case 12:
            return _context2.a(2);
        }
      }, _callee2, null, [[1, 10, 11, 12]]);
    }));
    return function (_x, _x2) {
      return _ref2.apply(this, arguments);
    };
  }(), [globalHeaders]);
  return {
    execute: execute,
    loading: loading,
    error: error
  };
};

/**
 * 使用通知的钩子
 * 
 * @returns {Object} 通知函数和状态
 */
export var useNotification = function useNotification() {
  var _useLLMManager3 = useLLMManager(),
    globalConfig = _useLLMManager3.globalConfig;
  var _useState1 = useState([]),
    _useState10 = _slicedToArray(_useState1, 2),
    notifications = _useState10[0],
    setNotifications = _useState10[1];
  var addNotification = useCallback(function (type, message) {
    var options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};
    if (!globalConfig.enableNotifications) return;
    var notification = _objectSpread({
      id: Date.now(),
      type: type,
      message: message,
      autoClose: options.autoClose !== false,
      // 默认自动关闭
      duration: options.duration || 5000
    }, options);
    setNotifications(function (prev) {
      return [].concat(_toConsumableArray(prev), [notification]);
    });
    if (notification.autoClose) {
      setTimeout(function () {
        removeNotification(notification.id);
      }, notification.duration);
    }
  }, [globalConfig.enableNotifications]);
  var removeNotification = useCallback(function (id) {
    setNotifications(function (prev) {
      return prev.filter(function (n) {
        return n.id !== id;
      });
    });
  }, []);
  var clearNotifications = useCallback(function () {
    setNotifications([]);
  }, []);
  return {
    notifications: notifications,
    addNotification: addNotification,
    removeNotification: removeNotification,
    clearNotifications: clearNotifications
  };
};

/**
 * 使用本地存储的钩子
 * 
 * @param {string} key - 存储键
 * @param {any} initialValue - 初始值
 * @returns {Array} 值和设置函数
 */
export var useLocalStorage = function useLocalStorage(key, initialValue) {
  // 从localStorage获取初始值
  var getStoredValue = function getStoredValue() {
    try {
      var item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error("\u4ECElocalStorage\u83B7\u53D6".concat(key, "\u5931\u8D25:"), error);
      return initialValue;
    }
  };
  var _useState11 = useState(getStoredValue),
    _useState12 = _slicedToArray(_useState11, 2),
    storedValue = _useState12[0],
    setStoredValue = _useState12[1];

  // 设置值到localStorage
  var setValue = function setValue(value) {
    try {
      var valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error("\u8BBE\u7F6ElocalStorage ".concat(key, " \u5931\u8D25:"), error);
    }
  };
  return [storedValue, setValue];
};

/**
 * 使用防抖的钩子
 * 
 * @param {any} value - 要防抖的值
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {any} 防抖后的值
 */
export var useDebounce = function useDebounce(value, delay) {
  var _useState13 = useState(value),
    _useState14 = _slicedToArray(_useState13, 2),
    debouncedValue = _useState14[0],
    setDebouncedValue = _useState14[1];
  useEffect(function () {
    var handler = setTimeout(function () {
      setDebouncedValue(value);
    }, delay);
    return function () {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
};

// 默认导出useLLMManager
export default useLLMManager;