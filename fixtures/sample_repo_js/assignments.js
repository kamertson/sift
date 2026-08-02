app.init = function init() {
  return true;
};

app.use = function(fn) {
  return fn;
};

Router.prototype.dispatch = function(req, res, next) {
  return next();
};

exports.foo = function() {
  return 42;
};

module.exports.bar = (x) => {
  return x;
};

app.render = (name, opts) => {
  return `${name}:${opts}`;
};

app.foo = 5;
