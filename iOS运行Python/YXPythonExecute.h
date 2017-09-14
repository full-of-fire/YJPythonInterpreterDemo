//
//  YXPythonExecute.h
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/12.
//  Copyright © 2017年 yj. All rights reserved.
//

#import <Foundation/Foundation.h>

@interface YXPythonExecute : NSObject
@property(nonatomic,copy,readonly) NSString *moduleName; //具体的模块名
@property(nonatomic,copy,readonly) NSString *moduleDirName; //模块的路径名
@property (nonatomic,assign,readonly) BOOL isRuning;
- (instancetype)initWithModuleDirName:(NSString*)moduleDirName moduleName:(NSString*)moduleName;

- (void)executeWithClass:(NSString*)className methodName:(NSString*)methodName parameter:(NSDictionary*)parameter success:(void(^)(id result))success fail:(void(^)(NSError* error))fail;
@end
