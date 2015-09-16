<?php if(!defined('BASEPATH')) exit('No direct script access allowed');
	
	class Api extends CI_Controller {

		var $api_key = "";

		function __construct()
	    {
			parent::__construct();

			$this->api_key = $this->input->post('api_key');

			if( $this->api_key){
				session_id( $this->api_key);
			}
			session_start(); //we need to call PHP's session object to access it through CI

			$this->load->model( 'user','',TRUE);
			$this->load->model( 'items','',TRUE);
			$this->load->helper( 'api_helper');
			$this->load->helper( 'string');
		}

		public function signin() {
			$email = $this->input->post('email');
			$password = $this->input->post('password');

			if (!trim($email) || !trim($password)) {
			    ret_make_response(101, "И-мэйл юм уу нууц үг хоосон байж болохгүй.");
			}

			//query the database
			$result = $this->user->login($email, $password);
			if($result){
			/*	$sess_array = array();*/
				foreach($result as $row){
				/*	$sess_array = array(
						'userid' => $row->id,
						'email' => $row->email
					);
					
					$this->session->set_userdata('logged_in', $sess_array);*/

					$_SESSION['userid']  =  $row->id;
					$_SESSION['email']  = $row->email;
				}
			}
			else{
				ret_make_response(102, "Ийм бүртгэл байхгүй эсвэл нууц үг буруу байна.");
			}

			$ret_resp = make_response(0, '');
			$ret_resp['api_key'] = session_id();
			ret_response($ret_resp);
		}
		
		public function signin_check() {
			$email = $this->input->post('email');
			$password = $this->input->post('password');

			if (!trim($email) || !trim($password)) {
			    ret_make_response(101, "И-мэйл юм уу нууц үг хоосон байж болохгүй.");
			}

			//query the database
			$result = $this->user->login($email, $password);
			if($result){

			}
			else{
				ret_make_response(102, "Нууц үг буруу байна.");
			}

			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}

		public function signout() {
			session_destroy();

			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}

		private function session_check(){
			if ( !trim($this->api_key)){
			    ret_make_response(101, "Нэвтрэх хандалт ажиллахгүй байна.");
			}
			else{			

				if(!isset( $_SESSION['email'])){
					ret_make_response(101, "Нэвтрэх хандалт ажиллахгүй байна.");
				}
			}
		}

		public function signleave() {
			$this->session_check();
			
			$email = $_SESSION['email'];
			$this->user->leave_member( $email);

			session_destroy();

			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}

		public function check_dup_id(){
			$email = $this->input->post('email');

			if (!trim($email)) {
			    ret_make_response(101, "ȸ�����̵� �����̸� �ȵ˴ϴ�.");
			}

			$user = $this->user->getUserinfowithemail( $email);
			if (!$user) {
				ret_make_response(0);
			} else {
				ret_make_response(102, '이미 존재하는 사용자입니다.');
			}
		}

		public function signup(){
			$name= $this->input->post('name');
			$email = $this->input->post('email');
			$password = $this->input->post('password');

			if ( !trim($name) || !trim($email) || !trim($password)) {
			    ret_make_response(101, "И-мэйл юм уу нууц үг хоосон байж болохгүй.");
			}

			$user = $this->user->getUserinfowithemail( $email);
			if ($user) {
				ret_make_response(102, 'Бүртгэлтэй хэрэглэгч байна.');
			}
			else{
				$insertid = $this->user->create_member3( $name, $email, $password);
				if ( !trim($insertid) ) {
					ret_make_response(103, "Бүртгүүлэх хэсэг мэдээлэлээс болоод бүтэлгүй боллоо.");
				}

				$_SESSION['userid'] = $insertid;
				$_SESSION['email']  =  $email;
			}

			
			$ret_resp = make_response(0, '');	
			$ret_resp['api_key'] = session_id();
			ret_response($ret_resp);
		}

		public function registerdevice(){
			$model_name= $this->input->post('model_name');
			$cpu_model = $this->input->post('cpu_model');
			$vendor_name = $this->input->post('vendor_name');
			$startsms = $this->input->post('lostdm_startsms');
			$stopsms = $this->input->post('lostdm_stopsms');

			if (!trim($model_name) || !trim($cpu_model) || !trim($vendor_name) || !trim($startsms) || !trim($stopsms)) {
			    ret_make_response(101, "Мэдээлэл хоосон зай байж болохгүй.");
			}

			$this->session_check();
			
			$email = $_SESSION['email'];			
			$userid = $_SESSION['userid'];
			$this->user->register_device( $email, $model_name, $cpu_model, $vendor_name, $startsms, $stopsms);
					
			$ret_resp = make_response(0, '');
			$ret_resp['deviceid'] = $userid;
			ret_response($ret_resp);
		}

		public function changepassword(){
			$pwd_new = $this->input->post('pwd_new');

			if (!trim($pwd_new)) {
			    ret_make_response(101, "Шинэ нууц үг хоосон зай байж болохгүй.");
			}

			$this->session_check();
			
			$email = $_SESSION['email'];
			$this->user->change_password( $email, $pwd_new);
					
			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}
		
		public function confirm_action(){
/*			$this->session_check();		
			$email = $_SESSION['email'];*/
		
			$userid = $this->input->post( 'deviceid');
			if (!trim($userid)) {
			    ret_make_response(101, "Төхөөрөмжийн ID хоосон зай байж болохгүй.");
			}

			$user = $this->user->getUserinfo( $userid);
			if( !$user ){
				ret_make_response(102, "Ийм төхөөрөмж алга байна.");
			}

			$expired = $user->expired;
			
			$ret_resp = make_response(0, '');	

//			if( $expired == '0')
			{
				$ret_resp['reports']['0'] = array( "name" => "camera",  "active" => get_boolstr( $user->reports_camera));
				$ret_resp['reports']['1'] = array( "name" => "location", "active" => get_boolstr( $user->reports_location));

				$ret_resp['actions']['0'] = array( "name" => "alarm", "active" => get_boolstr( $user->action_alarm), "param1" => "", "param2" => "");
				$ret_resp['actions']['1'] = array( "name" => "alert",  "active" => get_boolstr( $user->action_alert),  "param1" => $user->msg_alert, "param2" => "");
				$ret_resp['actions']['2'] = array( "name" => "lock", "active" => get_boolstr( $user->action_lock),  "param1" => $user->msg_lock, "param2" => "");
				$ret_resp['actions']['3'] = array( "name" => "contact", "active" => get_boolstr( $user->action_contact), "param1" => "", "param2" => "");
				$ret_resp['actions']['4'] = array( "name" => "sms", "active" => get_boolstr( $user->action_sms), "param1" => "", "param2" => "");
				$ret_resp['actions']['5'] = array( "name" => "photo", "active" => get_boolstr( $user->action_photo), "param1" => "", "param2" => "");
				$ret_resp['actions']['6'] = array( "name" => "music", "active" => get_boolstr( $user->action_music), "param1" => "", "param2" => "");
				$ret_resp['actions']['7'] = array( "name" => "memo", "active" => get_boolstr( $user->action_memo), "param1" => "", "param2" => "");
			/*	$ret_resp['1'] = array( "action2", $user->action2);
				$ret_resp['2'] = array( "action3", $user->action3);
				$ret_resp['3'] = array( "action4", $user->action4);
				$ret_resp['4'] = array( "action5", $user->action5);
				$ret_resp['5'] = array( "alertmsg", $user->alertmsg);*/

//				$this->user->set_expired( $userid);
			}
			ret_response($ret_resp);
		}

		public function report_upload(){
			/*$this->session_check();
			$userid = $_SESSION['userid'];		*/

			$userid = $this->input->post( 'deviceid');
			$ret_resp = make_response(0, '');	
			$szRandomName = random_string( 'alnum', 6);

			{
				$result = $this->items->do_upload( $szRandomName);

				if( empty( $result)){
					ret_make_response(103, "Бүртгүүлэх хэсэг мэдээлэлээс болоод бүтэлгүй боллоо.");
				}
				else{
					$uploaddata = $result['imagedata'];
					$uploaderror = $result['error'];
					
					if( $uploaderror == ''){
						$szImageName = $uploaddata['raw_name'];
						$szImagePath = "upload/" . $uploaddata['file_name'];
					}
					else{
						$szImagePath = "images/nocamera.png";
					}

					$insertid = $this->items->insert( $szImageName, $szImagePath, $userid);
					if ( !trim($insertid) ) {
						ret_make_response(103, "Бүртгүүлэх хэсэг мэдээлэлээс болоод бүтэлгүй боллоо.");
					}
					else{
						$ret_resp['reportid'] = $insertid;
					}
				}
			}
			
			ret_response($ret_resp);
		 }

		 public function contacts_upload(){
			/*$this->session_check();
			$userid = $_SESSION['userid'];		*/

			$userid = $this->input->post( 'deviceid');
			$itemid = $this->input->post( 'reportid');
			$ret_resp = make_response(0, '');	
			$szRandomName = random_string( 'alnum', 6);

			{
				$result = $this->items->do_contactupload( $szRandomName);

				$uploaddata = $result['contactdata'];
				$uploaderror = $result['error'];
				
				if( $uploaderror == ''){
					$szContactName = $uploaddata['raw_name'];
					$szContactPath = "upload/" . $uploaddata['file_name'];
				}
				else{
					$szContactPath = "";
				}

				if ( $this->items->update_contact( $itemid, $szContactPath) <= 0) {
					ret_make_response(102, "Ийм төхөөрөмж алга байна.");
				}
			}
			
			ret_response($ret_resp);
		 }

		/**************** Change Lost DM SMS **********/
		 public function change_startsms(){
			$startsms = $this->input->post('lostdm_startsms');

			if ( !trim($startsms)) {
			    ret_make_response(101, "Start SMS хоосон зай байж болохгүй.");
			}

			$this->session_check();
			
			$email = $_SESSION['email'];
			$this->user->change_startsms( $email, $startsms);
					
			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}

		 public function change_stopsms(){
			$stopsms = $this->input->post('lostdm_stopsms');

			if ( !trim($stopsms)) {
			    ret_make_response(101, "Stop SMS хоосон зай байж болохгүй.");
			}

			$this->session_check();
			
			$email = $_SESSION['email'];
			$this->user->change_stopsms( $email, $stopsms);
					
			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}

		public function registerdevice_status(){
			$set_miss = $this->input->post('set_miss');
			$userid = $this->input->post( 'deviceid');

			if ( !trim($userid)) {
				ret_make_response(101, "Төхөөрөмжийн ID хоосон зай байж болохгүй.");
			}

	/*		$this->session_check();
			$email = $_SESSION['email'];*/
			$this->user->registerdevice_status( $userid, $set_miss);
					
			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}

		public function registerdevice_pushid(){
			$pushid = $this->input->post('pushid');
			$userid = $this->input->post( 'deviceid');

			if ( !trim($pushid) || !trim($userid)) {
			    ret_make_response(101, "Төхөөрөмжийн ID мөн Push ID хоосон зай байж болохгүй.");
			}

			/*$this->session_check();			
			$email = $_SESSION['email'];*/

			if( $this->user->registerdevice_pushid( $userid, $pushid) <= 0){
				ret_make_response(102, "Ийм төхөөрөмж алга байна.");
			}
					
			$ret_resp = make_response(0, '');
			ret_response($ret_resp);
		}
	}
?>