//
//  YXPythonTestViewController.m
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/11.
//  Copyright © 2017年 yj. All rights reserved.
//

#import "YXPythonTestViewController.h"
#import "YXPythonInterpreter.h"

#import "NSString+YXAdd.h"

#import "YXPythonExecute.h"

#import "YXPyModuleManager.h"

@interface YXPythonTestViewController ()
@property (nonatomic,strong) YXPythonInterpreter * interPreter;
@property (nonatomic,strong) YXPythonExecute * execute;
@property(nonatomic,copy) NSString *deltePath;
@end

@implementation YXPythonTestViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    // Do any additional setup after loading the view from its nib.
    
    
    NSString *cib_url = @"http://192.168.188.100:8686/yanshu-app-web/static/python/creditcard/bank/cib.py";
    NSString *localPath = [[NSBundle mainBundle] pathForResource:@"Pybridge" ofType:@"py"];
    NSURL *localURl = [NSURL fileURLWithPath:localPath];
    
    
    NSLog(@"start = %f",CACurrentMediaTime());
    [YXPyModuleManager downLoadPyResourceToLoaclModuleWithModuelName:@"ICBC" pyURL:localURl complete:^(BOOL success) {
       
        if(!success) return;
        NSLog(@"start down load py form network =%f",CACurrentMediaTime());
        [YXPyModuleManager downLoadPyResourceToLoaclModuleWithModuelName:@"CIB" pyURL:[NSURL URLWithString:cib_url] complete:^(BOOL success) {
            if(!success) return ;
            
            NSLog(@"end = %f",CACurrentMediaTime());
            [self p_initMethod];
        }];
    }];
    
    
    
}


- (void)p_initMethod {

    YXPythonExecute *pythonExecute = [[YXPythonExecute alloc] initWithModuleDirName:@"ICBC" moduleName:@"Pybridge"];
    
    _execute = pythonExecute;
    
    NSDictionary *params = @{@"type":@"CIB",@"name":@"cib",@"class":@"Bank"};
    [pythonExecute executeWithClass:@"SpiderRouter" methodName:@"init" parameter:params success:^(id result) {
        
        NSLog(@"===resutl = %@",result);
    } fail:^(NSError *error) {
        NSLog(@"====error = %@",error.domain);
    }];
}



- (IBAction)dismissAction:(id)sender {
    
  
    
    if (_execute.isRuning) {
        
        NSLog(@"python 正在执行中不能退出该界面");
        
        return;
    }
    
      [self dismissViewControllerAnimated:YES completion:nil];
    
    [[NSFileManager defaultManager] removeItemAtPath:_deltePath error:nil];
    
}

- (IBAction)capture:(id)sender {
    
    /*{
     "username" : "6259612949434101",
     "password" : "714807",
     "zjhm" : "430482198807148077",
     "step" : "(null)",
     "flowNo" : "815cbc3fbb3b429cb3a6b9e69eaa9b64"
     }*/
    
    NSDictionary *parameter = @{@"username":@"6259612949434101",@"password":@"714807",@"zjhm":@"430482198807148077",@"flowNo":@"815cbc3fbb3b429cb3a6b9e69eaa9b64",@"step":@"null"};
    
    [_execute executeWithClass:@"SpiderRouter" methodName:@"execute" parameter:parameter success:^(id result) {
         NSLog(@"====执行成功====%@",result);
    } fail:^(NSError *error) {
        NSLog(@"执行错误 == %@",error.domain);
    }];
    
    

}

- (void)dealloc {

    [_interPreter finalize];
}

@end
