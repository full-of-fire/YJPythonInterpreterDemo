//
//  YXPythonInterpreter.h
//  iOS运行Python
//  ji
//  Created by  谭德林 on 2017/9/1.
//  Copyright © 2017年 yj. All rights reserved.
//

#import <Foundation/Foundation.h>
#import <Python/Python.h>
@interface YXPythonInterpreter : NSObject
@property (nonatomic,assign) BOOL running;
- (void)beginTask:(nonnull void (^)())task completion:(nullable void (^)())completion;
- (void)finalize;
@end
