//
//  ViewController.m
//  iOS运行Python
//
//  Created by  谭德林 on 2017/8/31.
//  Copyright © 2017年 yj. All rights reserved.
//

#import "ViewController.h"
#import <Python/Python.h>
#include <dlfcn.h>
#import "YXPythonTestViewController.h"
@interface ViewController ()

@end

@implementation ViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    // Do any additional setup after loading the view, typically from a nib.
    
    
}
- (IBAction)action:(id)sender {
    
    [self presentViewController:[YXPythonTestViewController new] animated:YES completion:nil];
}

+(BOOL)configPythonEnvironment
{
    
    NSBundle *mainBundle = [NSBundle mainBundle];
    
    NSString *bundlePath = [mainBundle pathForResource:@"PythonEnvironment" ofType:@"bundle"];
    
    BOOL isExist = [[NSFileManager defaultManager] fileExistsAtPath:bundlePath];
    
    if (isExist) {
        
        NSBundle *bundle = [NSBundle bundleWithPath:bundlePath];
        
        NSString *PythonPath = [bundle pathForResource:@"Python" ofType:@"framework"];
        
        isExist = [[NSFileManager defaultManager] fileExistsAtPath:PythonPath];
        
        if (isExist) {
            
            NSString *documantPath = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).lastObject;
            
            NSString *newFrameworkPath = [documantPath stringByAppendingPathComponent:@"Python.framework"];
            
            if (![[NSFileManager defaultManager] fileExistsAtPath:newFrameworkPath]) {
                NSError * error;
                [[NSFileManager defaultManager] copyItemAtPath:PythonPath toPath:newFrameworkPath error:&error];
                if (!error) {
                    return YES;
                }
            }
            else
            {
                return YES;
            }
        }
    }
    return NO;
    
}



- (void)didReceiveMemoryWarning {
    [super didReceiveMemoryWarning];
    // Dispose of any resources that can be recreated.
}


@end
