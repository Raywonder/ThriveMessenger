<?php
/**
 * Plugin Name: Thrive Server Sync
 * Description: Adds WordPress authentication support by linking WordPress accounts to a Thrive Messenger server without sharing WordPress passwords.
 * Version: 0.1.0
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
    private const UPDATE_FEED_URL = 'https://im.tappedin.fm/updates/thrive-server-sync.json';

    public static function init(): void {
        add_action('admin_menu', [__CLASS__, 'add_settings_page']);
        add_action('admin_init', [__CLASS__, 'register_settings']);
        add_action('user_register', [__CLASS__, 'sync_user_by_id'], 20, 1);
        add_action('profile_update', [__CLASS__, 'sync_user_by_id'], 20, 1);
        add_action('set_user_role', [__CLASS__, 'sync_user_by_id'], 20, 1);
        add_action('wp_login', [__CLASS__, 'sync_user_on_login'], 20, 2);
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
        if (version_compare((string) $info['version'], '0.1.0', '<=')) {
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
            'version' => (string) ($info['version'] ?? '0.1.0'),
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

    public static function register_rest_routes(): void {
        register_rest_route('thrive-server-sync/v1', '/provision-user', [
            'methods' => 'POST',
            'callback' => [__CLASS__, 'rest_provision_user'],
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
        $verified = self::verify_provision_signature($payload, $settings['sync_secret']);
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
        } else {
            $password = wp_generate_password(32, true, true);
            $user_id = wp_insert_user([
                'user_login' => $username,
                'user_email' => $email,
                'user_pass' => $password,
                'display_name' => $username,
                'role' => 'subscriber',
            ]);
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

    private static function sync_user(WP_User $user): void {
        $settings = self::get_settings();
        if ($settings['enabled'] !== '1' || trim($settings['sync_secret']) === '') {
            return;
        }

        $username = self::thrive_username($user);
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

    private static function verify_provision_signature(array $payload, string $secret) {
        $timestamp = (int) ($payload['timestamp'] ?? 0);
        $nonce = sanitize_text_field((string) ($payload['nonce'] ?? ''));
        $signature = strtolower(sanitize_text_field((string) ($payload['signature'] ?? '')));
        $username = self::sanitize_thrive_username((string) ($payload['username'] ?? ''));
        $email = sanitize_email((string) ($payload['email'] ?? ''));
        $is_admin = empty($payload['is_admin']) || $payload['is_admin'] === '0' ? '0' : '1';

        if (!$timestamp || $nonce === '' || $signature === '') {
            return 'Missing timestamp, nonce, or signature.';
        }
        if (abs(time() - $timestamp) > 300) {
            return 'Signature timestamp is outside the allowed window.';
        }
        $transient_key = 'thrive_sync_nonce_' . md5($nonce);
        if (get_transient($transient_key)) {
            return 'Replay detected.';
        }

        $expected = hash_hmac('sha256', implode("\n", [
            (string) $timestamp,
            $nonce,
            $username,
            $email,
            $is_admin,
        ]), $secret);
        if (!hash_equals($expected, $signature)) {
            return 'Invalid signature.';
        }
        set_transient($transient_key, '1', 10 * MINUTE_IN_SECONDS);
        return true;
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
