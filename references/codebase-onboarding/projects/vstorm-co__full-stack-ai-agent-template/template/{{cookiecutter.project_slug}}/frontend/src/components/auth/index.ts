{%- if cookiecutter.use_local_auth %}
export { LoginForm } from "./login-form";
export { RegisterForm } from "./register-form";
export { ForgotPasswordForm } from "./forgot-password-form";
{%- endif %}
export { OAuthButtons, OAuthDivider } from "./oauth-buttons";
