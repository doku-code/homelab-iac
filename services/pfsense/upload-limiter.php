<?php
/* The upload limiter of pfSense (operator's go, 2026-11-27). pfSense is not managed from this repository: this
 * file is the record of the one change made by hand through SSH, and the way to put it back after a reinstall.
 *   ssh -i ~/.ssh/pfsense_ed25519 admin@192.168.0.1 'php -f /dev/stdin' < services/pfsense/upload-limiter.php
 * One upload limiter with FQ-CoDel and its queue, and one floating match rule that sends everything leaving
 * through the WAN into it. Nothing for the download direction. A second run changes nothing.
 * To undo: Firewall > Rules > Floating (delete the rule), Firewall > Traffic Shaper > Limiters (delete WanUpload),
 * or restore /root/config-before-upload-limiter.xml (Diagnostics > Backup & Restore). */
require_once("config.inc");
require_once("functions.inc");
require_once("filter.inc");
require_once("shaper.inc");

$pipe = "WanUpload";
$queue = "WanUploadQ";
$mbit = "46";
$descr = "homelab-iac: upload below the line's 50 Mbit/s so that the queue forms here (FQ-CoDel), not in the modem";

$backup = "/root/config-before-upload-limiter.xml";
if (!file_exists($backup)) {
	copy("/cf/conf/config.xml", $backup);
	echo "backup: $backup\n";
}

$changed = false;
$limiters = config_get_path('dnshaper/queue', []);
if (!in_array($pipe, array_column($limiters, 'name'))) {
	$limiters[] = array(
		'name' => $pipe, 'number' => '1', 'qlimit' => '', 'plr' => '', 'description' => $descr,
		'bandwidth' => array('item' => array(array('bw' => $mbit, 'burst' => '', 'bwscale' => 'Mb', 'bwsched' => 'none'))),
		'enabled' => 'on', 'buckets' => '', 'mask' => 'none', 'maskbits' => '', 'maskbitsv6' => '', 'delay' => '0',
		'sched' => 'fq_codel',
		'param_fq_codel_target' => '5', 'param_fq_codel_interval' => '100', 'param_fq_codel_quantum' => '1514',
		'param_fq_codel_limit' => '10240', 'param_fq_codel_flows' => '1024',
		'aqm' => 'droptail', 'ecn' => '',
		'queue' => array(array(
			'name' => $queue, 'number' => '1', 'qlimit' => '', 'description' => 'everything that leaves through the WAN',
			'weight' => '', 'enabled' => 'on', 'buckets' => '', 'mask' => 'none', 'maskbits' => '', 'maskbitsv6' => '',
			'aqm' => 'droptail', 'ecn' => '',
		)),
	);
	config_set_path('dnshaper/queue', $limiters);
	$changed = true;
	echo "limiter $pipe ($mbit Mbit/s, fq_codel) with queue $queue added\n";
}

$rules = config_get_path('filter/rule', []);
$present = false;
foreach ($rules as $rule) {
	if (isset($rule['floating']) && ($rule['dnpipe'] ?? '') == $queue) {
		$present = true;
	}
}
if (!$present) {
	$rules[] = array(
		'id' => '', 'tracker' => (string)time(), 'type' => 'match', 'interface' => 'wan', 'ipprotocol' => 'inet',
		'tag' => '', 'tagged' => '', 'direction' => 'out', 'floating' => 'yes', 'max' => '', 'max-src-nodes' => '',
		'max-src-conn' => '', 'max-src-states' => '', 'statetimeout' => '', 'statetype' => 'keep state', 'os' => '',
		'source' => array('any' => ''), 'destination' => array('any' => ''),
		'gateway' => 'WAN_DHCP', 'dnpipe' => $queue,
		'descr' => 'homelab-iac: upload through the FQ-CoDel limiter',
		'created' => array('time' => (string)time(), 'username' => 'homelab-iac (ssh)'),
		'updated' => array('time' => (string)time(), 'username' => 'homelab-iac (ssh)'),
	);
	config_set_path('filter/rule', $rules);
	$changed = true;
	echo "floating match rule on WAN out added\n";
}

if ($changed) {
	write_config("homelab-iac: upload limiter $pipe ($mbit Mbit/s, FQ-CoDel) and its floating rule");
	$result = filter_configure_sync();
	echo "filter reloaded" . (is_null($result) ? "" : ": " . json_encode($result)) . "\n";
} else {
	echo "nothing to change\n";
}
