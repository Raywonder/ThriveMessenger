<?php
/**
 * Plugin Name: Thrive Server Sync
 * Description: Links WordPress and Thrive Messenger accounts, including secure password synchronization for linked accounts.
 * Version: 0.2.0
 * Author: Thrive Messenger contributors
 * License: GPL-2.0-or-later
 */

if (!defined('ABSPATH')) {
    exit;
}

final class Thrive_Server_Sync_Plugin {
    private const OPTION = 'thrive_server_sync_settings';
    private const META_LAST_SYNC = '_thrive_last_sync';
    private const META_LINKED_USERNAME = '_thrive_linked_username';
    private static array $pending_passwords = [];
    private static array $suppress_password_echo = [];
    private const UPDATE_FEED_URL = 'https://im.tappedin.fm/updates/thrive-server-sync.json';

    public static function init(): void {
        add_action('admin_menu', [__CLASS__, 'add_settings_page']);
        add_action('admin_init', [__CLASS__, 'register_settings']);
        add_action('user_register', [__CLASS__, 'sync_user_by_id'], 20, 1);
        add_action('profile_update', [__CLASS__, 'sync_user_by_id'], 20, 1);
        add_action('set_user_role', [__CLASS__, 'sync_user_by_id'], 20, 1);
        add_action('wp_login', [__CLASS__, 'sync_user_on_login'], 20, 2);
        add_filter('wp_pre_insert_user_data', [__CLASS__, 'capture_password_before_user_save'], 20, 4);
        add_action('wp_set_password', [__CLASS__, 'sync_password_after_set'], 20, 3);
        add_filter('authenticate', [__CLASS__, 'fallback_authenticate_with_thrive'], 30, 3);
        add_action('rest_api_init', [__CLASS__, 'register_rest_routes']);
        add_filter('pre_set_site_transient_update_plugins', [__CLASS__, 'check_for_plugin_update']);
        add_filter('plugins_api', [__CLASS__, 'plugin_info'], 10, 3);
    }

    public static function default_settings(): array {
        return [
            'enabled' => '0',
            'host' => 'im.tappedin.fm',
            'port' => '2005',
            'use_tls' => '0',
            'sync_secret' => '',
            'server_rest_url' => '',
            'provision_role' => 'subscriber',
            'update_feed_url' => self::UPDATE_FEED_URL,
        ];
    }

    public static function get_settings(): array {
        $saved = get_option(self::OPTION, []);
        if (!is_array($saved)) {
            $saved = [];
        }
        return array_merge(self::default_settings(), $saved);
    }

    public static function add_settings_page(): void {
        add_options_page(
            __('Thrive Server Sync', 'thrive-server-sync'),
            __('Thrive Server Sync', 'thrive-server-sync'),
            'manage_options',
            'thrive-server-sync',
            [__CLASS__, 'render_settings_page']
        );
    }

    public static function register_settings(): void {
        register_setting('thrive_server_sync', self::OPTION, [
            'type' => 'array',
            'sanitize_callback' => [__CLASS__, 'sanitize_settings'],
            'default' => self::default_settings(),
        ]);
    }

    public static function sanitize_settings($input): array {
        $input = is_array($input) ? $input : [];
        $defaults = self::default_settings();

        return [
            'enabled' => empty($input['enabled']) ? '0' : '1',
            'host' => sanitize_text_field($input['host'] ?? $defaults['host']),
            'port' => (string) max(1, min(65535, (int) ($input['port'] ?? $defaults['port']))),
            'use_tls' => empty($input['use_tls']) ? '0' : '1',
            'sync_secret' => sanitize_text_field($input['sync_secret'] ?? ''),
            'server_rest_url' => esc_url_raw($input['server_rest_url'] ?? ''),
            'provision_role' => sanitize_key($input['provision_role'] ?? 'subscriber'),
            'update_feed_url' => esc_url_raw($input['update_feed_url'] ?? $defaults['update_feed_url']),
        ];
    }

    public static function render_settings_page(): void {
        if (!current_user_can('manage_options')) {
            return;
        }
        $settings = self::get_settings();
        ?>
        <div class="wrap">
            <h1><?php esc_html_e('Thrive Server Sync', 'thrive-server-sync'); ?></h1>
            <form method="post" action="options.php">
                <?php settings_fields('thrive_server_sync'); ?>
                <table class="form-table" role="presentation">
                    <tr>
                        <th scope="row"><?php esc_html_e('Enable sync', 'thrive-server-sync'); ?></th>
                        <td>
                            <label>
                                <input type="checkbox" name="<?php echo esc_attr(self::OPTION); ?>[enabled]" value="1" <?php checked($settings['enabled'], '1'); ?>>
                                <?php esc_html_e('Sync WordPress users to Thrive Messenger', 'thrive-server-sync'); ?>
                            </label>
                            <p class="description"><?php esc_html_e('When enabled on both systems with the same secret, linked accounts use one password.', 'thrive-server-sync'); ?></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="thrive-sync-host"><?php esc_html_e('Thrive host', 'thrive-server-sync'); ?></label></th>
                        <td><input id="thrive-sync-host" class="regular-text" type="text" name="<?php echo esc_attr(self::OPTION); ?>[host]" value="<?php echo esc_attr($settings['host']); ?>"></td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="thrive-sync-port"><?php esc_html_e('Thrive port', 'thrive-server-sync'); ?></label></th>
                        <td><input id="thrive-sync-port" class="small-text" type="number" min="1" max="65535" name="<?php echo esc_attr(self::OPTION); ?>[port]" value="<?php echo esc_attr($settings['port']); ?>"></td>
                    </tr>
                    <tr>
                        <th scope="row"><?php esc_html_e('Connection security', 'thrive-server-sync'); ?></th>
                        <td>
                            <label>
                                <input type="checkbox" name="<?php echo esc_attr(self::OPTION); ?>[use_tls]" value="1" <?php checked($settings['use_tls'], '1'); ?>>
                                <?php esc_html_e('Use TLS for the Thrive server connection', 'thrive-server-sync'); ?>
                            </label>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="thrive-sync-secret"><?php esc_html_e('Sync secret', 'thrive-server-sync'); ?></label></th>
                        <td>
                            <input id="thrive-sync-secret" class="regular-text" type="password" autocomplete="new-password" name="<?php echo esc_attr(self::OPTION); ?>[sync_secret]" value="<?php echo esc_attr($settings['sync_secret']); ?>">
                            <p class="description"><?php esc_html_e('Use a long, unique secret that exactly matches the Thrive server configuration. Passwords are sent only over HTTPS and are never stored in this setting.', 'thrive-server-sync'); ?></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="thrive-server-rest-url"><?php esc_html_e('Thrive HTTPS sync URL', 'thrive-server-sync'); ?></label></th>
                        <td>
                            <input id="thrive-server-rest-url" class="regular-text code" type="url" inputmode="url" name="<?php echo esc_attr(self::OPTION); ?>[server_rest_url]" value="<?php echo esc_attr($settings['server_rest_url']); ?>" aria-describedby="thrive-server-rest-url-help">
                            <p id="thrive-server-rest-url-help" class="description"><?php esc_html_e('Required for password sync and fallback login. Example: https://messenger.example.com:2006', 'thrive-server-sync'); ?></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="thrive-provision-role"><?php esc_html_e('Role for accounts created from Thrive', 'thrive-server-sync'); ?></label></th>
                        <td>
                            <select id="thrive-provision-role" name="<?php echo esc_attr(self::OPTION); ?>[provision_role]" aria-describedby="thrive-provision-role-help">
                                <?php foreach (wp_roles()->get_names() as $role => $role_name) : ?>
                                    <option value="<?php echo esc_attr($role); ?>" <?php selected($settings['provision_role'], $role); ?>><?php echo esc_html($role_name); ?></option>
                                <?php endforeach; ?>
                            </select>
                            <p id="thrive-provision-role-help" class="description"><?php esc_html_e('New WordPress accounts created for Thrive users receive this role. Subscriber is the default.', 'thrive-server-sync'); ?></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="thrive-sync-update-feed"><?php esc_html_e('Plugin update feed', 'thrive-server-sync'); ?></label></th>
                        <td>
                            <input id="thrive-sync-update-feed" class="regular-text" type="url" name="<?php echo esc_attr(self::OPTION); ?>[update_feed_url]" value="<?php echo esc_attr($settings['update_feed_url']); ?>">
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }

    public static function check_for_plugin_update($transient) {
        if (!is_object($transient)) {
            return $transient;
        }
        $info = self::fetch_update_info();
        if (!$info || empty($info['version']) || empty($info['download_url'])) {
            return $transient;
        }
        $plugin_file = plugin_basename(__FILE__);
        if (version_compare((string) $info['version'], '0.2.0', '<=')) {
            return $transient;
        }
        $transient->response[$plugin_file] = (object) [
            'slug' => 'thrive-server-sync',
            'plugin' => $plugin_file,
            'new_version' => (string) $info['version'],
            'package' => esc_url_raw((string) $info['download_url']),
            'url' => esc_url_raw((string) ($info['homepage'] ?? 'https://im.tappedin.fm')),
        ];
        return $transient;
    }

    public static function plugin_info($result, string $action, $args) {
        if ($action !== 'plugin_information' || empty($args->slug) || $args->slug !== 'thrive-server-sync') {
            return $result;
        }
        $info = self::fetch_update_info();
        if (!$info) {
            return $result;
        }
        return (object) [
            'name' => 'Thrive Server Sync',
            'slug' => 'thrive-server-sync',
            'version' => (string) ($info['version'] ?? '0.2.0'),
            'author' => 'Thrive Messenger contributors',
            'homepage' => (string) ($info['homepage'] ?? 'https://im.tappedin.fm'),
            'download_link' => (string) ($info['download_url'] ?? ''),
            'sections' => [
                'description' => (string) ($info['description'] ?? 'Links WordPress users and admins to a Thrive Messenger server.'),
                'changelog' => (string) ($info['changelog'] ?? ''),
            ],
        ];
    }

    private static function fetch_update_info(): ?array {
        $settings = self::get_settings();
        $url = esc_url_raw((string) ($settings['update_feed_url'] ?? self::UPDATE_FEED_URL));
        if ($url === '') {
            return null;
        }
        $response = wp_remote_get($url, [
            'timeout' => 8,
            'headers' => ['Accept' => 'application/json'],
        ]);
        if (is_wp_error($response)) {
            return null;
        }
        $code = (int) wp_remote_retrieve_response_code($response);
        if ($code < 200 || $code >= 300) {
            return null;
        }
        $data = json_decode((string) wp_remote_retrieve_body($response), true);
        return is_array($data) ? $data : null;
    }

    public static function sync_user_on_login(string $user_login, WP_User $user): void {
        self::sync_user($user);
    }

    public static function sync_user_by_id(int $user_id): void {
        $user = get_user_by('id', $user_id);
        if ($user instanceof WP_User) {
            self::sync_user($user);
        }
    }

    public static function capture_password_before_user_save(array $data, bool $update, $user_id, array $userdata): array {
        $login = self::sanitize_thrive_username((string) ($data['user_login'] ?? $userdata['user_login'] ?? ''));
        $password = (string) ($userdata['user_pass'] ?? '');
        if ($login !== '' && $password !== '' && substr($password, 0, 1) !== '$') {
            self::$pending_passwords[$login] = $password;
        }
        return $data;
    }

    public static function sync_password_after_set(string $password, int $user_id, WP_User $old_user_data): void {
        if (!empty(self::$suppress_password_echo[(string) $user_id])) {
            return;
        }
        $user = get_user_by('id', $user_id);
        if ($user instanceof WP_User) {
            self::push_password_to_thrive($user, $password);
        }
    }

    public static function fallback_authenticate_with_thrive($user, string $username, string $password) {
        if (!$user instanceof WP_Error || $username === '' || $password === '') {
            return $user;
        }
        $wp_user = get_user_by('login', $username);
        if (!$wp_user instanceof WP_User || !self::verify_with_thrive($wp_user, $password)) {
            return $user;
        }
        self::$suppress_password_echo[(string) $wp_user->ID] = true;
        wp_set_password($password, (int) $wp_user->ID);
        unset(self::$suppress_password_echo[(string) $wp_user->ID]);
        return get_user_by('id', (int) $wp_user->ID);
    }

    public static function register_rest_routes(): void {
        register_rest_route('thrive-server-sync/v1', '/provision-user', [
            'methods' => 'POST',
            'callback' => [__CLASS__, 'rest_provision_user'],
            'permission_callback' => '__return_true',
        ]);
        register_rest_route('thrive-server-sync/v1', '/password', [
            'methods' => 'POST',
            'callback' => [__CLASS__, 'rest_set_password'],
            'permission_callback' => '__return_true',
        ]);
        register_rest_route('thrive-server-sync/v1', '/verify-password', [
            'methods' => 'POST',
            'callback' => [__CLASS__, 'rest_verify_password'],
            'permission_callback' => '__return_true',
        ]);
    }

    public static function rest_provision_user(WP_REST_Request $request) {
        $settings = self::get_settings();
        if ($settings['enabled'] !== '1' || trim($settings['sync_secret']) === '') {
            return new WP_REST_Response(['status' => 'error', 'reason' => 'Thrive Server Sync is disabled.'], 403);
        }

        $payload = $request->get_json_params();
        if (!is_array($payload)) {
            $payload = [];
        }
        $verified = self::verify_password_event($payload, $settings['sync_secret'], 'thrive', 'provision_user');
        if ($verified !== true) {
            return new WP_REST_Response(['status' => 'error', 'reason' => $verified], 403);
        }

        $username = self::sanitize_thrive_username($payload['username'] ?? '');
        $email = sanitize_email((string) ($payload['email'] ?? ''));
        if ($username === '' || $email === '' || !is_email($email)) {
            return new WP_REST_Response(['status' => 'error', 'reason' => 'Valid username and email are required.'], 400);
        }

        $user = get_user_by('login', $username);
        if (!$user) {
            $user = get_user_by('email', $email);
        }

        $created = false;
        if ($user instanceof WP_User) {
            $user_id = (int) $user->ID;
            self::$suppress_password_echo[(string) $user_id] = true;
            wp_set_password((string) $payload['password'], $user_id);
            unset(self::$suppress_password_echo[(string) $user_id]);
        } else {
            $password = (string) ($payload['password'] ?? '');
            if ($password === '') {
                return new WP_REST_Response(['status' => 'error', 'reason' => 'Password is required.'], 400);
            }
            self::$suppress_password_echo[$username] = true;
            $user_id = wp_insert_user([
                'user_login' => $username,
                'user_email' => $email,
                'user_pass' => $password,
                'display_name' => $username,
                'role' => self::provision_role($settings),
            ]);
            unset(self::$suppress_password_echo[$username]);
            if (is_wp_error($user_id)) {
                return new WP_REST_Response(['status' => 'error', 'reason' => $user_id->get_error_message()], 500);
            }
            $created = true;
            wp_new_user_notification((int) $user_id, null, 'user');
        }

        update_user_meta((int) $user_id, self::META_LINKED_USERNAME, $username);
        update_user_meta((int) $user_id, self::META_LAST_SYNC, [
            'time' => current_time('mysql', true),
            'status' => 'ok',
            'source' => 'thrive',
        ]);

        return [
            'status' => 'ok',
            'wp_user_id' => (string) $user_id,
            'username' => $username,
            'created' => $created,
            'linked' => true,
        ];
    }

    public static function rest_set_password(WP_REST_Request $request) {
        $settings = self::get_settings();
        $payload = $request->get_json_params();
        $payload = is_array($payload) ? $payload : [];
        $verified = self::verify_password_event($payload, $settings['sync_secret'], 'thrive', 'thrive_set_password');
        if ($settings['enabled'] !== '1' || $verified !== true) {
            return new WP_REST_Response(['status' => 'error', 'reason' => $verified === true ? 'Thrive Server Sync is disabled.' : $verified], 403);
        }
        $user = get_user_by('id', (int) ($payload['wp_user_id'] ?? 0));
        if (!$user instanceof WP_User || self::thrive_username($user) !== self::sanitize_thrive_username((string) ($payload['username'] ?? ''))) {
            return new WP_REST_Response(['status' => 'error', 'reason' => 'Linked WordPress user was not found.'], 404);
        }
        self::$suppress_password_echo[(string) $user->ID] = true;
        wp_set_password((string) $payload['password'], (int) $user->ID);
        unset(self::$suppress_password_echo[(string) $user->ID]);
        return ['status' => 'ok'];
    }

    public static function rest_verify_password(WP_REST_Request $request) {
        $settings = self::get_settings();
        $payload = $request->get_json_params();
        $payload = is_array($payload) ? $payload : [];
        $verified = self::verify_password_event($payload, $settings['sync_secret'], 'thrive', 'verify_thrive_password');
        if ($settings['enabled'] !== '1' || $verified !== true) {
            return new WP_REST_Response(['status' => 'error', 'reason' => $verified === true ? 'Thrive Server Sync is disabled.' : $verified], 403);
        }
        $user = get_user_by('id', (int) ($payload['wp_user_id'] ?? 0));
        $matched = $user instanceof WP_User && self::thrive_username($user) === self::sanitize_thrive_username((string) ($payload['username'] ?? ''))
            && wp_check_password((string) $payload['password'], (string) $user->user_pass, (int) $user->ID);
        return ['status' => 'ok', 'matched' => $matched];
    }

    private static function sync_user(WP_User $user): void {
        $settings = self::get_settings();
        if ($settings['enabled'] !== '1' || trim($settings['sync_secret']) === '') {
            return;
        }

        $username = self::thrive_username($user);
        if (!empty(self::$suppress_password_echo[$username])) {
            return;
        }
        $is_admin = user_can($user, 'manage_options') ? '1' : '0';
        $timestamp = (string) time();
        $nonce = wp_generate_password(24, false, false);
        $payload = [
            'action' => 'wordpress_sync_user',
            'timestamp' => $timestamp,
            'nonce' => $nonce,
            'wp_user_id' => (string) $user->ID,
            'username' => $username,
            'email' => (string) $user->user_email,
            'wp_login' => (string) $user->user_login,
            'is_admin' => $is_admin,
        ];
        $payload['signature'] = self::signature($payload, $settings['sync_secret']);

        $result = self::send_payload($payload, $settings);
        update_user_meta($user->ID, self::META_LAST_SYNC, [
            'time' => current_time('mysql', true),
            'status' => $result['status'] ?? 'error',
            'reason' => $result['reason'] ?? '',
        ]);

        if (($result['status'] ?? '') === 'ok') {
            update_user_meta($user->ID, self::META_LINKED_USERNAME, $username);
            if (isset(self::$pending_passwords[$username])) {
                $password = self::$pending_passwords[$username];
                unset(self::$pending_passwords[$username]);
                self::push_password_to_thrive($user, $password);
            }
        }
    }

    private static function thrive_username(WP_User $user): string {
        $username = strtolower((string) $user->user_login);
        $username = preg_replace('/[^a-z0-9_.-]+/', '', $username);
        $username = trim((string) $username, '._-');
        if ($username === '') {
            $username = 'wpuser' . (int) $user->ID;
        }
        return substr($username, 0, 64);
    }

    private static function sanitize_thrive_username(string $username): string {
        $username = strtolower($username);
        $username = preg_replace('/[^a-z0-9_.-]+/', '', $username);
        $username = trim((string) $username, '._-');
        return substr($username, 0, 64);
    }

    private static function signature(array $payload, string $secret): string {
        return hash_hmac('sha256', implode("\n", [
            (string) $payload['timestamp'],
            (string) $payload['nonce'],
            (string) $payload['wp_user_id'],
            (string) $payload['username'],
            (string) $payload['email'],
            (string) $payload['is_admin'],
        ]), $secret);
    }

    private static function password_digest(string $password): string {
        return hash('sha256', $password);
    }

    private static function password_signature(array $payload, string $secret): string {
        return hash_hmac('sha256', implode("\n", [
            (string) ($payload['action'] ?? ''), (string) ($payload['timestamp'] ?? ''), (string) ($payload['nonce'] ?? ''),
            (string) ($payload['wp_user_id'] ?? ''), (string) ($payload['username'] ?? ''), (string) ($payload['email'] ?? ''),
            (string) ($payload['is_admin'] ?? ''), (string) ($payload['origin'] ?? ''), (string) ($payload['password_digest'] ?? ''),
        ]), $secret);
    }

    private static function verify_password_event(array $payload, string $secret, string $origin, string $action) {
        $timestamp = (int) ($payload['timestamp'] ?? 0);
        $nonce = sanitize_text_field((string) ($payload['nonce'] ?? ''));
        $signature = strtolower(sanitize_text_field((string) ($payload['signature'] ?? '')));
        $password = (string) ($payload['password'] ?? '');
        if (!$timestamp || $nonce === '' || $signature === '' || $password === '' || ($payload['origin'] ?? '') !== $origin || ($payload['action'] ?? '') !== $action) {
            return 'Missing timestamp, nonce, or signature.';
        }
        if (abs(time() - $timestamp) > 300) {
            return 'Signature timestamp is outside the allowed window.';
        }
        $transient_key = 'thrive_sync_nonce_' . md5($nonce);
        if (get_transient($transient_key)) {
            return 'Replay detected.';
        }

        $payload['password_digest'] = self::password_digest($password);
        $expected = self::password_signature($payload, $secret);
        if (!hash_equals($expected, $signature)) {
            return 'Invalid signature.';
        }
        set_transient($transient_key, '1', 10 * MINUTE_IN_SECONDS);
        return true;
    }

    private static function provision_role(array $settings): string {
        $role = sanitize_key((string) ($settings['provision_role'] ?? 'subscriber'));
        return array_key_exists($role, wp_roles()->get_names()) ? $role : 'subscriber';
    }

    private static function password_event(WP_User $user, string $password, string $action, string $origin): array {
        $payload = [
            'action' => $action,
            'timestamp' => (string) time(),
            'nonce' => wp_generate_password(24, false, false),
            'wp_user_id' => (string) $user->ID,
            'username' => self::thrive_username($user),
            'email' => (string) $user->user_email,
            'wp_login' => (string) $user->user_login,
            'is_admin' => user_can($user, 'manage_options') ? '1' : '0',
            'origin' => $origin,
            'password' => $password,
        ];
        $payload['password_digest'] = self::password_digest($password);
        return $payload;
    }

    private static function post_to_thrive(string $path, array $payload, array $settings): array {
        $base = rtrim((string) ($settings['server_rest_url'] ?? ''), '/');
        if (strpos($base, 'https://') !== 0) {
            return ['status' => 'skipped'];
        }
        $payload['signature'] = self::password_signature($payload, (string) $settings['sync_secret']);
        $response = wp_remote_post($base . $path, ['timeout' => 12, 'headers' => ['Content-Type' => 'application/json'], 'body' => wp_json_encode($payload)]);
        if (is_wp_error($response)) {
            return ['status' => 'error'];
        }
        $decoded = json_decode((string) wp_remote_retrieve_body($response), true);
        return is_array($decoded) ? $decoded : ['status' => 'error'];
    }

    private static function push_password_to_thrive(WP_User $user, string $password): void {
        $settings = self::get_settings();
        if ($settings['enabled'] !== '1' || trim((string) $settings['sync_secret']) === '') {
            return;
        }
        self::post_to_thrive('/thrive-server-sync/v1/password', self::password_event($user, $password, 'wordpress_set_password', 'wordpress'), $settings);
    }

    private static function verify_with_thrive(WP_User $user, string $password): bool {
        $settings = self::get_settings();
        if ($settings['enabled'] !== '1' || trim((string) $settings['sync_secret']) === '') {
            return false;
        }
        $result = self::post_to_thrive('/thrive-server-sync/v1/verify-password', self::password_event($user, $password, 'verify_wordpress_password', 'wordpress'), $settings);
        return !empty($result['matched']);
    }

    private static function send_payload(array $payload, array $settings): array {
        $host = trim((string) $settings['host']);
        $port = (int) $settings['port'];
        if ($host === '' || $port < 1 || $port > 65535) {
            return ['status' => 'error', 'reason' => 'Invalid Thrive server settings.'];
        }

        $scheme = $settings['use_tls'] === '1' ? 'ssl://' : 'tcp://';
        $target = $scheme . $host . ':' . $port;
        $errno = 0;
        $errstr = '';
        $context = null;
        if ($settings['use_tls'] === '1') {
            $context = stream_context_create([
                'ssl' => [
                    'verify_peer' => false,
                    'verify_peer_name' => false,
                ],
            ]);
        }
        $socket = @stream_socket_client($target, $errno, $errstr, 8, STREAM_CLIENT_CONNECT, $context);
        if (!$socket) {
            return ['status' => 'error', 'reason' => 'Could not connect to Thrive server.'];
        }

        stream_set_timeout($socket, 8);
        fwrite($socket, wp_json_encode($payload) . "\n");
        $line = fgets($socket, 8192);
        fclose($socket);

        $decoded = is_string($line) ? json_decode($line, true) : null;
        if (!is_array($decoded)) {
            return ['status' => 'error', 'reason' => 'Invalid response from Thrive server.'];
        }
        return $decoded;
    }
}

Thrive_Server_Sync_Plugin::init();
