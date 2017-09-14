//
//  YXPythonInterpreter.m
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/1.
//  Copyright © 2017年 yj. All rights reserved.
//

#import "YXPythonInterpreter.h"

@interface YXPythonInterpreter ()

@property (nonatomic,assign) dispatch_queue_t pythonQueue;
@end

@implementation YXPythonInterpreter


- (instancetype)init
{
    self = [super init];
    if (self) {
        [self initialize];
    }
    return self;
}

- (void)dealloc{
    [self finalize];
}


- (void)initialize
{
    [self p_setupHomePath];
    Py_Initialize();
    PyEval_InitThreads();
    if (Py_IsInitialized()) {
        NSLog(@"初始化环境成功");
    }
    self.running = YES;
    
}

- (void)beginTask:(nonnull void (^)())task completion:(nullable void (^)())completion
{
   
    dispatch_async(self.pythonQueue, ^{
        
        task();
          __weak typeof(self) weakSelf = self;
        if (completion){
            dispatch_async(dispatch_get_main_queue(), ^{
                weakSelf.running = NO;
                completion();
            });
        }
    });
}


- (void)finalize
{
    Py_Finalize();
    self.running = NO;
}


#pragma mark - private 

- (void)p_setupHomePath {
    const char * frameworkPath = [[NSString stringWithFormat:@"%@/Resources",[self p_pythonFrameworkPath]] UTF8String];
    wchar_t  *pythonHome = _Py_char2wchar(frameworkPath, NULL);
    Py_SetPythonHome(pythonHome);
}

- (NSString*)p_pythonFrameworkPath{
    NSString *documantPath = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).lastObject;
    NSString *newFrameworkPath = [documantPath stringByAppendingPathComponent:@"Python.framework"];
    return newFrameworkPath;
}


#pragma mark - lazy
- (dispatch_queue_t)pythonQueue {
    if (_pythonQueue== nil) {
        _pythonQueue = dispatch_get_global_queue(0, 0);
    }
    return _pythonQueue;
}


@end
