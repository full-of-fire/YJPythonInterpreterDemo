//
//  YXPyModuleManager.h
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/13.
//  Copyright © 2017年 yj. All rights reserved.
//

#import <Foundation/Foundation.h>

@interface YXPyModuleManager : NSObject
@property(nonatomic,copy,readonly) NSString *moduleName;
@property(nonatomic,copy,readonly) NSURL *pyURL;


- (instancetype)initWithMoudleName:(NSString*)moduleName
                             pyURL:(NSURL*)pyURL;

- (void)downLoadPyResourceToLoaclModuleComplete:(void(^)(BOOL success))complete;

+ (void)downLoadPyResourceToLoaclModuleWithModuelName:(NSString*)moduleName pyURL:(NSURL*)pyURL complete:(void(^)(BOOL success))complete;
@end
